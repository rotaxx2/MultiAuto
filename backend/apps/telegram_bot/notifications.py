from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from django.conf import settings

from .bot import create_bot

logger = logging.getLogger(__name__)


def send_telegram_message(telegram_id: int | None, text: str) -> bool:
    if not telegram_id or not settings.TELEGRAM_BOT_TOKEN:
        return False

    async def _send() -> None:
        bot = create_bot()
        try:
            await bot.send_message(chat_id=telegram_id, text=text)
        finally:
            await bot.session.close()

    try:
        async_to_sync(_send)()
    except Exception:
        logger.exception("Failed to send Telegram message to %s.", telegram_id)
        return False
    return True
