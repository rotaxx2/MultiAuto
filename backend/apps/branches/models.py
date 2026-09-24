from __future__ import annotations

import uuid

from django.db import models

from apps.organizations.models import Organization


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="branches_org_name_uq"),
        ]
        indexes = [
            models.Index(fields=["organization"], name="branches_org_idx"),
            models.Index(fields=["organization", "is_active"], name="branches_org_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.name}"
