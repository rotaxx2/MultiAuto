from __future__ import annotations

import uuid

from django.db import models

from apps.branches.models import Branch


class Workstation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="workstations")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch__organization__name", "branch__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="workstations_branch_name_uq"),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"], name="workstations_branch_active_idx"),
        ]

    @property
    def organization_id(self):
        return self.branch.organization_id

    def __str__(self) -> str:
        return f"{self.branch.name}: {self.name}"
