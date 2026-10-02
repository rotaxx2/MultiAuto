from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.telegram_bot.notifications import send_telegram_message

from ..models import BLOCKING_BOOKING_STATUSES, BookingReminder, BookingReminderStatus
from .booking_service import format_booking_message

logger = logging.getLogger(__name__)

ReminderSender = Callable[[int | None, str], bool]


class ReminderDeliveryError(RuntimeError):
    """Raised when a reminder was due but the notification layer did not deliver it."""


def sanitize_error_message(error: object, *, fallback: str = "Delivery failed.") -> str:
    message = str(error) or fallback
    redacted = message.replace("\n", " ").replace("\r", " ").strip()
    for marker in ("bot", "token", "authorization", "password", "secret", "database_url"):
        if marker in redacted.lower():
            return fallback
    return redacted[:500]


def get_due_booking_reminder_ids(*, now=None) -> list[UUID]:
    current_time = now or timezone.now()
    return list(
        BookingReminder.objects.filter(
            sent_at__isnull=True,
            status=BookingReminderStatus.PENDING,
            attempts=0,
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
    delivery_error: ReminderDeliveryError | None = None
    delivered_successfully = False
    logger.info("Booking reminder delivery started. reminder_id=%s", reminder_id)

    with transaction.atomic():
        reminder = (
            BookingReminder.objects.select_for_update()
            .select_related("booking__branch", "booking__car", "booking__client", "booking__service")
            .get(id=reminder_id)
        )
        booking = reminder.booking
        if reminder.sent_at or reminder.status == BookingReminderStatus.SENT:
            logger.info("Booking reminder already sent. reminder_id=%s booking_id=%s", reminder.id, booking.id)
            return False
        if reminder.status == BookingReminderStatus.CANCELLED:
            logger.info("Booking reminder already cancelled. reminder_id=%s booking_id=%s", reminder.id, booking.id)
            return False
        if reminder.scheduled_at > current_time:
            logger.info("Booking reminder is not due yet. reminder_id=%s booking_id=%s", reminder.id, booking.id)
            return False
        if booking.status not in BLOCKING_BOOKING_STATUSES or booking.start_at <= current_time:
            logger.info("Booking reminder skipped. reminder_id=%s booking_id=%s status=%s", reminder.id, booking.id, booking.status)
            reminder.status = BookingReminderStatus.CANCELLED
            reminder.error_message = "Booking is no longer active for reminder delivery."
            reminder.save(update_fields=["status", "error_message"])
            return False

        attempt_time = timezone.now()
        reminder.attempts += 1
        reminder.last_attempt_at = attempt_time
        reminder.save(update_fields=["attempts", "last_attempt_at"])
        try:
            delivered = reminder_sender(booking.client.telegram_id, format_booking_message(booking, _reminder_prefix(reminder.kind)))
        except Exception as exc:
            error_message = sanitize_error_message(exc)
            reminder.error_message = error_message
            reminder.save(update_fields=["error_message"])
            logger.warning(
                "Booking reminder delivery raised. reminder_id=%s booking_id=%s kind=%s attempts=%s",
                reminder.id,
                booking.id,
                reminder.kind,
                reminder.attempts,
            )
            delivery_error = ReminderDeliveryError(error_message)
            delivered = False
        if not delivered:
            if delivery_error is None:
                error_message = "Telegram delivery returned unsuccessful result."
                reminder.error_message = error_message
                reminder.save(update_fields=["error_message"])
                delivery_error = ReminderDeliveryError(error_message)
                logger.warning(
                    "Booking reminder delivery failed. reminder_id=%s booking_id=%s kind=%s attempts=%s",
                    reminder.id,
                    booking.id,
                    reminder.kind,
                    reminder.attempts,
                )
            return_after_error = True
        else:
            return_after_error = False

        if not return_after_error:
            reminder.sent_at = timezone.now()
            reminder.status = BookingReminderStatus.SENT
            reminder.error_message = ""
            reminder.save(update_fields=["sent_at", "status", "error_message"])
            logger.info("Booking reminder delivered. reminder_id=%s booking_id=%s kind=%s", reminder.id, booking.id, reminder.kind)
            delivered_successfully = True

    if delivery_error is not None:
        raise delivery_error
    return delivered_successfully


def mark_booking_reminder_failed(reminder_id: UUID | str, error: object) -> None:
    with transaction.atomic():
        try:
            reminder = BookingReminder.objects.select_for_update().get(id=reminder_id)
        except BookingReminder.DoesNotExist:
            return
        if reminder.sent_at or reminder.status == BookingReminderStatus.SENT:
            return
        reminder.status = BookingReminderStatus.FAILED
        reminder.error_message = sanitize_error_message(error)
        reminder.save(update_fields=["status", "error_message"])


def reset_failed_booking_reminder(reminder: BookingReminder) -> None:
    reminder.status = BookingReminderStatus.PENDING
    reminder.error_message = ""
    reminder.save(update_fields=["status", "error_message"])


def process_due_booking_reminders(*, sender: ReminderSender | None = None, now=None) -> int:
    sent = 0
    for reminder_id in get_due_booking_reminder_ids(now=now):
        if send_booking_reminder(reminder_id, sender=sender, now=now):
            sent += 1
    return sent

