from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.organizations.models import Organization


class UserRole(models.TextChoices):
    CLIENT = "CLIENT", "Client"
    ADMIN = "ADMIN", "Admin"
    OWNER = "OWNER", "Owner"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CLIENT)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "role"], name="accounts_org_role_idx"),
            models.Index(fields=["telegram_id"], name="accounts_telegram_idx"),
            models.Index(fields=["is_active"], name="accounts_active_idx"),
        ]

    def __str__(self) -> str:
        return self.username or str(self.telegram_id) or str(self.id)

    @property
    def is_client(self) -> bool:
        return self.role == UserRole.CLIENT

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER
