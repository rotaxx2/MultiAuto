from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .celery import app as celery_app


class HealthCheckTests(SimpleTestCase):
    @patch("config.health._check_redis", return_value=(True, "ok"))
    @patch("config.health._check_database", return_value=(True, "ok"))
    def test_health_returns_ok_when_dependencies_are_available(self, _database, _redis) -> None:
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("config.health._check_redis", return_value=(True, "ok"))
    @patch("config.health._check_database", return_value=(False, "unavailable"))
    def test_health_returns_unavailable_when_database_fails(self, _database, _redis) -> None:
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["database"], "unavailable")

    @patch("config.health._check_redis", return_value=(False, "unavailable"))
    @patch("config.health._check_database", return_value=(True, "ok"))
    def test_health_returns_unavailable_when_redis_fails(self, _database, _redis) -> None:
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["redis"], "unavailable")

    @patch("config.health._check_redis", return_value=(True, "ok"))
    @patch("config.health.celery_app")
    def test_celery_health_returns_ok_when_worker_replies(self, celery, _redis) -> None:
        inspector = Mock()
        inspector.ping.return_value = {"worker@example": {"ok": "pong"}}
        celery.control.inspect.return_value = inspector

        response = self.client.get("/health/celery/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["celery_worker"], "ok")

    @patch("config.health._check_redis", return_value=(True, "ok"))
    @patch("config.health.celery_app")
    def test_celery_health_returns_unavailable_without_worker_reply(self, celery, _redis) -> None:
        inspector = Mock()
        inspector.ping.return_value = None
        celery.control.inspect.return_value = inspector

        response = self.client.get("/health/celery/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["celery_worker"], "unavailable")


class ProductionConfigurationTests(SimpleTestCase):
    def test_celery_configuration_uses_redis_broker(self) -> None:
        self.assertTrue(celery_app.conf.broker_url.startswith("redis://"))

    def test_production_settings_require_secret_key(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(backend_dir)
        env["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
        env["SECRET_KEY"] = ""
        env["ALLOWED_HOSTS"] = "example.com"
        result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY must be set", result.stderr + result.stdout)

