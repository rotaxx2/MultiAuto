from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.telegram_bot.notifications import send_telegram_message

from ..models import BLOCKING_BOOKING_STATUSES, BookingReminder
from .booking_service import format_booking_message

logger = logging.getLogger(__name__)

ReminderSender = Callable[[int | None, str], bool]


class ReminderDeliveryError(RuntimeError):
    """Raised when a reminder was due but the notification layer did not deliver it."""


def get_due_booking_reminder_ids(*, now=None) -> list[UUID]:
    current_time = now or timezone.now()
    return list(
        BookingReminder.objects.filter(
            sent_at__isnull=True,
            scheduled_at__lte=current_time,
            booking__start_at__gt=current_time,
            booking__status__in=BLOCKING_BOOKING_STATUSES,
        )
        .order_by("scheduled_at")
        .values_list("id", flat=True)
    )


def _reminder_prefix(kind: str) -> str:
    if kind == "DAY_BEFORE":
        return "Напоминание: завтра у вас запись на автомойку."
    return "Напоминание: через 1 час у вас запись на автомойку."


def send_booking_reminder(reminder_id: UUID | str, *, sender: ReminderSender | None = None, now=None) -> bool:
    current_time = now or timezone.now()
    reminder_sender = sender or send_telegram_message
    logger.info("Booking reminder delivery started. reminder_id=%s", reminder_id)

    with transaction.atomic():
        reminder = (
            BookingReminder.objects.select_for_update()
            .select_related("booking__branch", "booking__car", "booking__client", "booking__service")
            .get(id=reminder_id)
        )
        booking = reminder.booking
        if reminder.sent_at:
            logger.info("Booking reminder already sent. reminder_id=%s booking_id=%s", reminder.id, booking.id)
            return False
        if reminder.scheduled_at > current_time:
            logger.info("Booking reminder is not due yet. reminder_id=%s booking_id=%s", reminder.id, booking.id)
            return False
        if booking.status not in BLOCKING_BOOKING_STATUSES or booking.start_at <= current_time:
            logger.info("Booking reminder skipped. reminder_id=%s booking_id=%s status=%s", reminder.id, booking.id, booking.status)
            return False

        delivered = reminder_sender(booking.client.telegram_id, format_booking_message(booking, _reminder_prefix(reminder.kind)))
        if not delivered:
            logger.warning("Booking reminder delivery failed. reminder_id=%s booking_id=%s kind=%s", reminder.id, booking.id, reminder.kind)
            raise ReminderDeliveryError(f"Reminder {reminder.id} was not delivered.")

        reminder.sent_at = timezone.now()
        reminder.save(update_fields=["sent_at"])
        logger.info("Booking reminder delivered. reminder_id=%s booking_id=%s kind=%s", reminder.id, booking.id, reminder.kind)
        return True


def process_due_booking_reminders(*, sender: ReminderSender | None = None, now=None) -> int:
    sent = 0
    for reminder_id in get_due_booking_reminder_ids(now=now):
        if send_booking_reminder(reminder_id, sender=sender, now=now):
            sent += 1
    return sent

