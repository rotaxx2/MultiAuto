from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.conf import settings

from .services import TelegramUserData, get_or_create_client_from_telegram, resolve_organization

logger = logging.getLogger(__name__)
router = Router()


def build_mini_app_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Открыть запись",
            web_app=WebAppInfo(url=settings.TELEGRAM_MINI_APP_URL),
        )
    )
    return builder


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить Telegram-пользователя.")
        return

    if not settings.TELEGRAM_MINI_APP_URL:
        logger.error("TELEGRAM_MINI_APP_URL is not configured.")
        await message.answer("Mini App временно недоступен. Попробуйте позже.")
        return

    command = message.text or ""
    parts = command.split(maxsplit=1)
    start_payload = parts[1].strip() if len(parts) > 1 else ""
    organization = await sync_to_async(resolve_organization)(start_payload)

    if organization is None:
        await message.answer("Автомойка не найдена или временно недоступна.")
        return

    telegram_user = TelegramUserData(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or "",
    )
    await sync_to_async(get_or_create_client_from_telegram)(telegram_user, organization)

    await message.answer(
        "Здравствуйте! Нажмите кнопку ниже, чтобы открыть запись на автомойку.",
        reply_markup=build_mini_app_keyboard().as_markup(),
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


def create_bot() -> Bot:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
