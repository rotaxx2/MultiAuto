from __future__ import annotations

import asyncio
import logging

from django.core.management.base import BaseCommand

from apps.telegram_bot.bot import create_bot, create_dispatcher

logger = logging.getLogger(__name__)


async def run_polling(bot, dispatcher) -> None:  # type: ignore[no-untyped-def]
    logger.info("Starting Telegram bot polling.")
    try:
        # Long polling cannot run while a webhook is active. Keep pending updates
        # intact so deploys and restarts do not silently drop user messages.
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Telegram bot polling stopped by shutdown signal.")
        raise
    except Exception:
        logger.exception("Telegram bot polling stopped after an unexpected error.")
        raise
    finally:
        await bot.session.close()
        logger.info("Telegram bot HTTP session closed.")


class Command(BaseCommand):
    help = "Run Telegram bot polling."

    def handle(self, *args: object, **options: object) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        bot = create_bot()
        dispatcher = create_dispatcher()
        await run_polling(bot, dispatcher)
