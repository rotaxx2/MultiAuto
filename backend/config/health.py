from __future__ import annotations

import logging

import redis
from celery.exceptions import CeleryError
from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .celery import app as celery_app

logger = logging.getLogger(__name__)


def _check_database() -> tuple[bool, str]:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check database dependency failed.")
        return False, "unavailable"
    return True, "ok"


def _check_redis() -> tuple[bool, str]:
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
    except Exception:
        logger.exception("Health check Redis dependency failed.")
        return False, "unavailable"
    return True, "ok"


@require_GET
def health(request):  # noqa: ANN001
    database_ok, database_status = _check_database()
    redis_ok, redis_status = _check_redis()
    ok = database_ok and redis_ok
    status_code = 200 if ok else 503
    payload = {
        "status": "ok" if ok else "error",
        "checks": {
            "application": "ok",
            "database": database_status,
            "redis": redis_status,
        },
    }
    return JsonResponse(payload, status=status_code)


@require_GET
def celery_health(request):  # noqa: ANN001
    redis_ok, redis_status = _check_redis()
    worker_ok = False
    worker_status = "unavailable"
    if redis_ok:
        try:
            replies = celery_app.control.inspect(timeout=1).ping()
            worker_ok = bool(replies)
            worker_status = "ok" if worker_ok else "unavailable"
        except CeleryError:
            logger.exception("Health check Celery worker dependency failed.")
        except Exception:
            logger.exception("Health check Celery worker dependency failed.")

    ok = redis_ok and worker_ok
    status_code = 200 if ok else 503
    payload = {
        "status": "ok" if ok else "error",
        "checks": {
            "redis": redis_status,
            "celery_worker": worker_status,
        },
    }
    return JsonResponse(payload, status=status_code)

