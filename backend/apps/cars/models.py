from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def normalize_license_plate(value: str) -> str:
    return "".join(value.upper().split())


class Car(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cars")
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    license_plate = models.CharField(max_length=32)
    color = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["brand", "model", "license_plate"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "license_plate"], name="cars_owner_plate_uq"),
        ]
        indexes = [
            models.Index(fields=["owner"], name="cars_owner_idx"),
            models.Index(fields=["owner", "license_plate"], name="cars_owner_plate_idx"),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        self.license_plate = normalize_license_plate(self.license_plate)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.license_plate})"
