from __future__ import annotations

import asyncio

from aiogram.types import MenuButtonWebApp, WebAppInfo
from django.core.management.base import BaseCommand

from apps.telegram_bot.bot import create_bot, get_mini_app_url


class Command(BaseCommand):
    help = "Configure the Telegram bot menu button as a Web App button."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--text", default="Записаться", help="Menu button text shown in Telegram.")
        parser.add_argument("--url", default="", help="Optional Mini App URL override.")

    def handle(self, *args: object, **options: object) -> None:
        asyncio.run(self._run(text=options["text"], url=options["url"]))

    async def _run(self, *, text: str, url: str) -> None:
        mini_app_url = url.strip() or get_mini_app_url()
        bot = create_bot()
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text=text,
                    web_app=WebAppInfo(url=mini_app_url),
                )
            )
        finally:
            await bot.session.close()

        self.stdout.write(self.style.SUCCESS(f"Telegram menu button configured: {mini_app_url}"))
