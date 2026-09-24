from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.branches.models import Branch
from apps.cars.models import Car
from apps.organizations.models import Organization
from apps.services.models import Service
from apps.workstations.models import Workstation


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    ARRIVED = "ARRIVED", "Arrived"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    READY = "READY", "Ready"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_SHOW = "NO_SHOW", "No show"


BLOCKING_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.ARRIVED,
    BookingStatus.IN_PROGRESS,
    BookingStatus.READY,
)


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="bookings")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="bookings")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    car = models.ForeignKey(Car, on_delete=models.PROTECT, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    workstation = models.ForeignKey(Workstation, on_delete=models.PROTECT, related_name="bookings")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    client_comment = models.TextField(blank=True)
    admin_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["organization", "branch", "start_at"], name="book_org_branch_start_idx"),
            models.Index(fields=["client", "start_at"], name="book_client_start_idx"),
            models.Index(fields=["workstation", "start_at", "end_at"], name="book_ws_time_idx"),
            models.Index(fields=["organization", "status"], name="book_org_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.service.name} at {self.start_at.isoformat()}"
