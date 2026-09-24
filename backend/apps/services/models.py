from __future__ import annotations

import uuid

from django.db import models

from apps.organizations.models import Organization


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="services_org_name_uq"),
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0), name="services_duration_positive"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="services_price_non_negative"),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="services_org_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name
