from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from apps.branches.models import Branch
from apps.schedules.services import get_branch_schedule
from apps.services.models import Service
from apps.workstations.models import Workstation

from ..models import BLOCKING_BOOKING_STATUSES, Booking

SLOT_INTERVAL_MINUTES = 30


@dataclass(frozen=True)
class AvailableSlot:
    start_at: datetime
    end_at: datetime


def overlaps_existing_booking(workstation: Workstation, start_at: datetime, end_at: datetime) -> bool:
    return Booking.objects.filter(
        workstation=workstation,
        status__in=BLOCKING_BOOKING_STATUSES,
        start_at__lt=end_at,
        end_at__gt=start_at,
    ).exists()


def get_available_slots(branch: Branch, service: Service, target_date: date) -> list[AvailableSlot]:
    schedule = get_branch_schedule(branch, target_date)
    if schedule.is_closed or not schedule.opening_time or not schedule.closing_time or not service.is_active:
        return []

    branch_tz = ZoneInfo(branch.timezone)
    local_start = datetime.combine(target_date, schedule.opening_time, tzinfo=branch_tz)
    local_close = datetime.combine(target_date, schedule.closing_time, tzinfo=branch_tz)
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=SLOT_INTERVAL_MINUTES)
    workstations = list(Workstation.objects.filter(branch=branch, is_active=True))
    if not workstations:
        return []

    slots: list[AvailableSlot] = []
    cursor = local_start
    while cursor + duration <= local_close:
        start_at = cursor.astimezone(datetime_timezone.utc)
        end_at = (cursor + duration).astimezone(datetime_timezone.utc)
        if any(not overlaps_existing_booking(workstation, start_at, end_at) for workstation in workstations):
            slots.append(AvailableSlot(start_at=start_at, end_at=end_at))
        cursor += step
    return slots
