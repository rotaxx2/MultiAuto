from __future__ import annotations

import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from ..models import Booking, BookingStatus
from .booking_service import cancel_pending_booking_reminders

logger = logging.getLogger(__name__)

AUTO_NO_SHOW_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)
LIFECYCLE_BATCH_SIZE = 100


def get_overdue_booking_ids(*, now=None, limit: int = LIFECYCLE_BATCH_SIZE) -> list[UUID]:
    current_time = now or timezone.now()
    return list(
        Booking.objects.filter(
            status__in=AUTO_NO_SHOW_STATUSES,
            end_at__lt=current_time,
        )
        .order_by("end_at", "id")
        .values_list("id", flat=True)[:limit]
    )


def mark_booking_no_show_if_overdue(booking_id: UUID | str, *, now=None) -> bool:
    current_time = now or timezone.now()
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(id=booking_id)
        if booking.status not in AUTO_NO_SHOW_STATUSES:
            return False
        if booking.end_at >= current_time:
            return False

        previous_status = booking.status
        booking.status = BookingStatus.NO_SHOW
        booking.save(update_fields=["status", "updated_at"])
        cancel_pending_booking_reminders(booking, "Booking was automatically marked as no-show.")
        logger.info(
            "Booking automatically marked no-show. booking_id=%s previous_status=%s end_at=%s",
            booking.id,
            previous_status,
            booking.end_at.isoformat(),
        )
        return True


def process_overdue_bookings(*, now=None, limit: int = LIFECYCLE_BATCH_SIZE) -> int:
    updated = 0
    for booking_id in get_overdue_booking_ids(now=now, limit=limit):
        if mark_booking_no_show_if_overdue(booking_id, now=now):
            updated += 1
    return updated
