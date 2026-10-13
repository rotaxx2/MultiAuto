from __future__ import annotations

import logging
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.conf import settings

from .services import TelegramUserData, get_or_create_client_from_telegram, resolve_organization

logger = logging.getLogger(__name__)
router = Router()


def get_mini_app_url() -> str:
    mini_app_url = settings.TELEGRAM_MINI_APP_URL.strip()
    parsed_url = urlparse(mini_app_url)

    if not mini_app_url:
        raise ValueError("TELEGRAM_MINI_APP_URL is not configured.")
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("TELEGRAM_MINI_APP_URL must be an absolute HTTPS URL for Telegram Mini Apps.")

    return mini_app_url


def validate_bot_settings() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    get_mini_app_url()


def build_mini_app_keyboard() -> InlineKeyboardBuilder:
    mini_app_url = get_mini_app_url()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Открыть запись",
            web_app=WebAppInfo(url=mini_app_url),
        )
    )
    return builder


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить Telegram-пользователя.")
        return

    try:
        get_mini_app_url()
    except ValueError as exc:
        logger.error("%s", exc)
        await message.answer("Mini App временно недоступен. Попробуйте позже.")
        return

    command = message.text or ""
    parts = command.split(maxsplit=1)
    start_payload = parts[1].strip() if len(parts) > 1 else ""
    organization = await sync_to_async(resolve_organization, thread_sensitive=False)(start_payload)

    if organization is None:
        await message.answer("Автомойка не найдена или временно недоступна.")
        return

    telegram_user = TelegramUserData(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or "",
    )
    await sync_to_async(get_or_create_client_from_telegram, thread_sensitive=False)(telegram_user, organization)

    await message.answer(
        "Здравствуйте! Нажмите кнопку ниже, чтобы открыть запись на автомойку.",
        reply_markup=build_mini_app_keyboard().as_markup(),
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


def create_bot() -> Bot:
    validate_bot_settings()
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
