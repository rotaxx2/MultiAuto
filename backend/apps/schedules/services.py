from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from apps.branches.models import Branch

from .models import BusinessHour, ScheduleException


@dataclass(frozen=True)
class BranchSchedule:
    is_closed: bool
    opening_time: time | None
    closing_time: time | None
    source: str
    reason: str = ""


def get_branch_schedule(branch: Branch, target_date: date) -> BranchSchedule:
    exception = ScheduleException.objects.filter(branch=branch, date=target_date).first()
    if exception:
        return BranchSchedule(
            is_closed=exception.is_closed,
            opening_time=None if exception.is_closed else exception.opening_time,
            closing_time=None if exception.is_closed else exception.closing_time,
            source="exception",
            reason=exception.reason,
        )

    business_hour = BusinessHour.objects.filter(branch=branch, weekday=target_date.weekday()).first()
    if not business_hour:
        return BranchSchedule(is_closed=True, opening_time=None, closing_time=None, source="business_hour")

    return BranchSchedule(
        is_closed=business_hour.is_closed,
        opening_time=None if business_hour.is_closed else business_hour.opening_time,
        closing_time=None if business_hour.is_closed else business_hour.closing_time,
        source="business_hour",
    )
