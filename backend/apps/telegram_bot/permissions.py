from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole


class IsClient(BasePermission):
    message = "Only client users can access this endpoint."

    def has_permission(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == UserRole.CLIENT
        )
