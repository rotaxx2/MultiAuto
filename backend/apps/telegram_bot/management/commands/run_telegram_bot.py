from __future__ import annotations

import asyncio
import logging

from django.core.management.base import BaseCommand

from apps.telegram_bot.bot import create_bot, create_dispatcher

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run Telegram bot polling."

    def handle(self, *args: object, **options: object) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        bot = create_bot()
        dispatcher = create_dispatcher()
        logger.info("Starting Telegram bot polling.")
        await dispatcher.start_polling(bot)
