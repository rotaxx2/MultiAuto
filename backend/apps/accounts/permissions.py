from __future__ import annotations

from typing import Protocol

from django.db.models import Model, QuerySet

from .models import User, UserRole


class TenantScopedModel(Protocol):
    organization_id: object


def is_admin_or_owner(user: User) -> bool:
    return user.is_authenticated and user.role in {UserRole.ADMIN, UserRole.OWNER}


def is_owner(user: User) -> bool:
    return user.is_authenticated and user.role == UserRole.OWNER


def belongs_to_user_organization(user: User, obj: TenantScopedModel) -> bool:
    """Object-level tenant guard for models carrying organization_id."""
    return bool(user.organization_id and obj.organization_id == user.organization_id)


def for_user_organization(queryset: QuerySet[Model], user: User) -> QuerySet[Model]:
    """Apply the default tenant filter; views must use this before object lookup."""
    if not user.is_authenticated or not user.organization_id:
        return queryset.none()
    return queryset.filter(organization_id=user.organization_id)
