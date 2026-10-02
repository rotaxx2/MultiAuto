from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from .services.reminder_service import ReminderDeliveryError, get_due_booking_reminder_ids, mark_booking_reminder_failed, send_booking_reminder

logger = logging.getLogger(__name__)


@shared_task(name="apps.bookings.tasks.process_due_booking_reminders")
def process_due_booking_reminders() -> int:
    reminder_ids = get_due_booking_reminder_ids()
    logger.info("Booking reminder scan started. due_count=%s", len(reminder_ids))
    for reminder_id in reminder_ids:
        send_booking_reminder_task.delay(str(reminder_id))
    return len(reminder_ids)


@shared_task(bind=True, name="apps.bookings.tasks.send_booking_reminder")
def send_booking_reminder_task(self, reminder_id: str) -> bool:
    try:
        return send_booking_reminder(reminder_id)
    except ReminderDeliveryError as exc:
        if self.request.retries >= settings.CELERY_BOOKING_REMINDER_MAX_RETRIES:
            mark_booking_reminder_failed(reminder_id, exc)
            logger.error(
                "Booking reminder final failure. reminder_id=%s retries=%s",
                reminder_id,
                self.request.retries,
            )
            return False
        logger.warning("Booking reminder task retry scheduled. reminder_id=%s retries=%s", reminder_id, self.request.retries)
        raise self.retry(
            exc=exc,
            countdown=settings.CELERY_BOOKING_REMINDER_RETRY_COUNTDOWN,
            max_retries=settings.CELERY_BOOKING_REMINDER_MAX_RETRIES,
        )
