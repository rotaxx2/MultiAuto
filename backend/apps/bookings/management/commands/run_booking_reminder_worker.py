from __future__ import annotations

import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run a lightweight booking reminder worker."

    def handle(self, *args: object, **options: object) -> None:
        interval = settings.BOOKING_REMINDER_POLL_SECONDS
        self.stdout.write(self.style.SUCCESS(f"Booking reminder worker started. Interval: {interval}s"))
        while True:
            call_command("send_booking_reminders")
            time.sleep(interval)
