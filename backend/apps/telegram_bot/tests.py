from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import time
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlencode

from asgiref.sync import async_to_sync
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization

from .auth import validate_telegram_init_data
from .bot import build_mini_app_keyboard, create_bot, handle_start
from .management.commands import run_telegram_bot
from .services import TelegramUserData, get_or_create_client_from_telegram


def signed_init_data(user: dict, bot_token: str, auth_date: int | None = None) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test-query",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


class TelegramStartTests(TestCase):
    def test_start_handler_uses_telegram_user_data_service(self) -> None:
        source = inspect.getsource(handle_start)

        self.assertIn("TelegramUserData", source)
        self.assertIn("get_or_create_client_from_telegram", source)
        self.assertIn("build_mini_app_keyboard", source)

    @override_settings(TELEGRAM_MINI_APP_URL="https://example.com/mini-app")
    def test_mini_app_keyboard_uses_web_app_button(self) -> None:
        markup = build_mini_app_keyboard().as_markup()

        button = markup.inline_keyboard[0][0]
        self.assertEqual(button.text, "Открыть запись")
        self.assertEqual(button.web_app.url, "https://example.com/mini-app")

    @override_settings(TELEGRAM_MINI_APP_URL="http://localhost:5173")
    def test_mini_app_keyboard_rejects_non_https_url(self) -> None:
        with self.assertRaisesMessage(ValueError, "absolute HTTPS URL"):
            build_mini_app_keyboard()

    def _message(self, text: str, telegram_id: int, username: str, first_name: str, last_name: str):
        message = Mock()
        message.text = text
        message.answer = AsyncMock()
        message.from_user = Mock(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        return message


class TelegramServiceTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Clean Auto", slug="clean-auto")

    def test_repeated_start_does_not_create_duplicate(self) -> None:
        get_or_create_client_from_telegram(
            TelegramUserData(telegram_id=1002, username="old_name"),
            self.organization,
        )

        get_or_create_client_from_telegram(
            TelegramUserData(telegram_id=1002, username="new_name", first_name="Anna", last_name="Ivanova"),
            self.organization,
        )

        self.assertEqual(User.objects.filter(telegram_id=1002).count(), 1)

    def test_start_updates_telegram_user_information(self) -> None:
        user, _ = get_or_create_client_from_telegram(
            TelegramUserData(telegram_id=1003, username="old_name", first_name="Old"),
            self.organization,
        )

        get_or_create_client_from_telegram(
            TelegramUserData(telegram_id=1003, username="new_name", first_name="New", last_name="User"),
            self.organization,
        )

        user.refresh_from_db()
        self.assertEqual(user.username, "new_name")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")


class TelegramAuthTests(TestCase):
    bot_token = "123456:test-token"

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Clean Auto", slug="clean-auto")

    @override_settings(TELEGRAM_BOT_TOKEN=bot_token, TELEGRAM_AUTH_MAX_AGE_SECONDS=86400)
    def test_validates_telegram_init_data(self) -> None:
        init_data = signed_init_data({"id": 2001, "username": "client"}, self.bot_token)

        result = validate_telegram_init_data(init_data)

        self.assertEqual(result.telegram_id, 2001)
        self.assertEqual(result.username, "client")

    @override_settings(TELEGRAM_BOT_TOKEN=bot_token, TELEGRAM_AUTH_MAX_AGE_SECONDS=60)
    def test_rejects_expired_telegram_init_data(self) -> None:
        init_data = signed_init_data(
            {"id": 2002, "username": "client"},
            self.bot_token,
            auth_date=int(time.time()) - 120,
        )

        with self.assertRaisesMessage(Exception, "expired"):
            validate_telegram_init_data(init_data)

    @override_settings(TELEGRAM_BOT_TOKEN=bot_token, TELEGRAM_AUTH_MAX_AGE_SECONDS=86400)
    def test_auth_endpoint_returns_token_for_verified_client(self) -> None:
        client = APIClient()
        init_data = signed_init_data({"id": 2003, "username": "client"}, self.bot_token)

        response = client.post(
            "/api/v1/client/auth/telegram",
            {"init_data": init_data, "start_param": "org_clean-auto"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["telegram_id"], 2003)
        self.assertEqual(User.objects.get(telegram_id=2003).organization, self.organization)

    @override_settings(TELEGRAM_BOT_TOKEN=bot_token, TELEGRAM_AUTH_MAX_AGE_SECONDS=86400)
    def test_me_requires_authenticated_client(self) -> None:
        client = APIClient()

        response = client.get("/api/me/")

        self.assertEqual(response.status_code, 401)

    def test_client_cannot_access_another_user_profile_by_id(self) -> None:
        user = User.objects.create_user(
            username="client-one",
            telegram_id=2004,
            role=UserRole.CLIENT,
            organization=self.organization,
        )
        other = User.objects.create_user(
            username="client-two",
            telegram_id=2005,
            role=UserRole.CLIENT,
            organization=self.organization,
        )
        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.get(f"/api/me/?user_id={other.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(user.id))
        self.assertNotEqual(response.data["id"], str(other.id))

    @patch("apps.telegram_bot.auth.hmac.compare_digest", return_value=False)
    @override_settings(TELEGRAM_BOT_TOKEN=bot_token)
    def test_rejects_invalid_telegram_signature(self, _compare_digest: Mock) -> None:
        init_data = signed_init_data({"id": 2006}, self.bot_token)

        response = APIClient().post(
            "/api/v1/client/auth/telegram",
            {"init_data": init_data, "start_param": "org_clean-auto"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)


class TelegramPollingCommandTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_MINI_APP_URL="https://example.com/mini-app")
    def test_create_bot_requires_token(self) -> None:
        with self.assertRaisesMessage(RuntimeError, "TELEGRAM_BOT_TOKEN is not configured"):
            create_bot()

    def test_polling_preserves_pending_updates_in_startup_code(self) -> None:
        source = inspect.getsource(run_telegram_bot.run_polling)

        self.assertIn("drop_pending_updates=False", source)
        self.assertNotIn("drop_pending_updates=True", source)

    def test_polling_error_log_does_not_include_token_setting(self) -> None:
        source = inspect.getsource(run_telegram_bot.run_polling)

        self.assertIn("logger.exception", source)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", source)
