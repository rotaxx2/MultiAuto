from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class TelegramInitData:
    telegram_id: int
    username: str
    first_name: str
    last_name: str
    auth_date: int
    raw_user: dict[str, Any]


def validate_telegram_init_data(init_data: str, bot_token: str | None = None) -> TelegramInitData:
    """Validate Telegram Mini App init data and return trusted user information."""
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValidationError("Telegram bot token is not configured.")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValidationError("Telegram init data hash is missing.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValidationError("Telegram init data signature is invalid.")

    try:
        auth_date = int(parsed["auth_date"])
    except (KeyError, ValueError) as exc:
        raise ValidationError("Telegram init data auth_date is invalid.") from exc

    max_age = settings.TELEGRAM_AUTH_MAX_AGE_SECONDS
    if int(time.time()) - auth_date > max_age:
        raise ValidationError("Telegram init data is expired.")

    try:
        raw_user = json.loads(parsed["user"])
        telegram_id = int(raw_user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValidationError("Telegram init data user payload is invalid.") from exc

    return TelegramInitData(
        telegram_id=telegram_id,
        username=raw_user.get("username", "") or "",
        first_name=raw_user.get("first_name", "") or "",
        last_name=raw_user.get("last_name", "") or "",
        auth_date=auth_date,
        raw_user=raw_user,
    )
