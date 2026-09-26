from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.branches.models import Branch
from apps.schedules.services import get_branch_schedule
from apps.services.models import Service
from apps.workstations.models import Workstation

from ..models import BLOCKING_BOOKING_STATUSES, Booking

SLOT_INTERVAL_MINUTES = 30
BOOKING_DAYS_AHEAD = 2


@dataclass(frozen=True)
class AvailableSlot:
    start_at: datetime
    end_at: datetime
    total_workstations: int
    occupied_workstations: int
    free_workstations: int
    is_available: bool


@dataclass(frozen=True)
class AvailableDate:
    date: date
    label: str
    is_available: bool


def get_allowed_booking_dates(branch: Branch) -> list[AvailableDate]:
    branch_tz = ZoneInfo(branch.timezone)
    today = timezone.now().astimezone(branch_tz).date()
    labels = ("Сегодня", "Завтра", "Послезавтра")
    dates: list[AvailableDate] = []
    for offset in range(BOOKING_DAYS_AHEAD + 1):
        target_date = today + timedelta(days=offset)
        schedule = get_branch_schedule(branch, target_date)
        dates.append(
            AvailableDate(
                date=target_date,
                label=labels[offset],
                is_available=not schedule.is_closed and bool(schedule.opening_time and schedule.closing_time),
            )
        )
    return dates


def is_booking_date_allowed(branch: Branch, target_date: date) -> bool:
    return target_date in {item.date for item in get_allowed_booking_dates(branch)}


def overlaps_existing_booking(workstation: Workstation, start_at: datetime, end_at: datetime) -> bool:
    return Booking.objects.filter(
        workstation=workstation,
        status__in=BLOCKING_BOOKING_STATUSES,
        start_at__lt=end_at,
        end_at__gt=start_at,
    ).exists()


def count_occupied_workstations(workstations: list[Workstation], start_at: datetime, end_at: datetime) -> int:
    workstation_ids = [workstation.id for workstation in workstations]
    if not workstation_ids:
        return 0
    return (
        Booking.objects.filter(
            workstation_id__in=workstation_ids,
            status__in=BLOCKING_BOOKING_STATUSES,
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        .values("workstation_id")
        .distinct()
        .count()
    )


def get_available_slots(branch: Branch, service: Service, target_date: date) -> list[AvailableSlot]:
    if not is_booking_date_allowed(branch, target_date):
        return []

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
    now = timezone.now()
    while cursor + duration <= local_close:
        start_at = cursor.astimezone(datetime_timezone.utc)
        end_at = (cursor + duration).astimezone(datetime_timezone.utc)
        if start_at <= now:
            cursor += step
            continue
        occupied = count_occupied_workstations(workstations, start_at, end_at)
        total = len(workstations)
        free = max(total - occupied, 0)
        if free > 0:
            slots.append(
                AvailableSlot(
                    start_at=start_at,
                    end_at=end_at,
                    total_workstations=total,
                    occupied_workstations=occupied,
                    free_workstations=free,
                    is_available=True,
                )
            )
        cursor += step
    return slots
