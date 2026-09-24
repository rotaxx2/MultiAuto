from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.branches.models import Branch


class BusinessHour(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="business_hours")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch__name", "weekday"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "weekday"], name="biz_hours_branch_weekday_uq"),
        ]
        indexes = [
            models.Index(fields=["branch", "weekday"], name="biz_hours_branch_weekday_idx"),
        ]

    @property
    def organization_id(self):
        return self.branch.organization_id

    def clean(self) -> None:
        if self.is_closed:
            return
        if not self.opening_time or not self.closing_time:
            raise ValidationError("Opening and closing time are required for open days.")
        if self.opening_time >= self.closing_time:
            raise ValidationError("Opening time must be earlier than closing time.")

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class ScheduleException(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="schedule_exceptions")
    date = models.DateField()
    is_closed = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch__name", "date"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "date"], name="sched_exc_branch_date_uq"),
        ]
        indexes = [
            models.Index(fields=["branch", "date"], name="sched_exc_branch_date_idx"),
        ]

    @property
    def organization_id(self):
        return self.branch.organization_id

    def clean(self) -> None:
        if self.is_closed:
            return
        if not self.opening_time or not self.closing_time:
            raise ValidationError("Opening and closing time are required for open exceptions.")
        if self.opening_time >= self.closing_time:
            raise ValidationError("Opening time must be earlier than closing time.")

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
