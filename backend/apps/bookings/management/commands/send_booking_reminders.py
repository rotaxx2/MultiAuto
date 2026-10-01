from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.bookings.services.reminder_service import process_due_booking_reminders


class Command(BaseCommand):
    help = "Send due booking reminders once."

    def handle(self, *args: object, **options: object) -> None:
        sent = process_due_booking_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sent reminders: {sent}"))
