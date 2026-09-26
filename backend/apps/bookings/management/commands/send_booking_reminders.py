from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import BLOCKING_BOOKING_STATUSES, BookingReminder
from apps.bookings.services.booking_service import format_booking_message
from apps.telegram_bot.notifications import send_telegram_message


class Command(BaseCommand):
    help = "Send due booking reminders once."

    def handle(self, *args: object, **options: object) -> None:
        now = timezone.now()
        sent = 0

        due_reminders = (
            BookingReminder.objects.select_related("booking__branch", "booking__car", "booking__client", "booking__service")
            .filter(sent_at__isnull=True, scheduled_at__lte=now, booking__start_at__gt=now, booking__status__in=BLOCKING_BOOKING_STATUSES)
            .order_by("scheduled_at")
        )

        for reminder in due_reminders:
            with transaction.atomic():
                locked = (
                    BookingReminder.objects.select_for_update()
                    .select_related("booking__branch", "booking__car", "booking__client", "booking__service")
                    .get(id=reminder.id)
                )
                if locked.sent_at or locked.booking.status not in BLOCKING_BOOKING_STATUSES or locked.booking.start_at <= now:
                    continue

                if locked.kind == "DAY_BEFORE":
                    prefix = "Напоминание: завтра у вас запись на автомойку."
                else:
                    prefix = "Напоминание: через 1 час у вас запись на автомойку."

                send_telegram_message(locked.booking.client.telegram_id, format_booking_message(locked.booking, prefix))
                locked.sent_at = timezone.now()
                locked.save(update_fields=["sent_at"])
                sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent reminders: {sent}"))
