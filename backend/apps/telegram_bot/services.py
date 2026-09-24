from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization


@dataclass(frozen=True)
class TelegramUserData:
    telegram_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""


def resolve_organization(start_payload: str = "") -> Organization | None:
    slug = ""
    if start_payload.startswith("org_"):
        slug = start_payload.removeprefix("org_")
    elif settings.TELEGRAM_DEFAULT_ORGANIZATION_SLUG:
        slug = settings.TELEGRAM_DEFAULT_ORGANIZATION_SLUG

    if not slug:
        return None

    return Organization.objects.filter(slug=slug, is_active=True).first()


def telegram_username_or_fallback(telegram_id: int, username: str = "") -> str:
    if username:
        candidate = slugify(username).replace("-", "_")
        if candidate:
            return candidate[:150]
    return f"tg_{telegram_id}"


@transaction.atomic
def get_or_create_client_from_telegram(
    telegram_user: TelegramUserData,
    organization: Organization | None,
) -> tuple[User, bool]:
    defaults = {
        "username": telegram_username_or_fallback(telegram_user.telegram_id, telegram_user.username),
        "first_name": telegram_user.first_name,
        "last_name": telegram_user.last_name,
        "role": UserRole.CLIENT,
        "organization": organization,
        "is_active": True,
    }
    user, created = User.objects.select_for_update().get_or_create(
        telegram_id=telegram_user.telegram_id,
        defaults=defaults,
    )

    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user, True

    fields_to_update: list[str] = []
    for field_name in ("first_name", "last_name"):
        new_value = getattr(telegram_user, field_name)
        if new_value and getattr(user, field_name) != new_value:
            setattr(user, field_name, new_value)
            fields_to_update.append(field_name)

    if telegram_user.username:
        new_username = telegram_username_or_fallback(telegram_user.telegram_id, telegram_user.username)
        username_taken = User.objects.exclude(id=user.id).filter(username=new_username).exists()
        if not username_taken and user.username != new_username:
            user.username = new_username
            fields_to_update.append("username")

    if organization and user.organization_id is None:
        user.organization = organization
        fields_to_update.append("organization")

    if user.role != UserRole.CLIENT:
        return user, False

    if fields_to_update:
        fields_to_update.append("updated_at")
        user.save(update_fields=fields_to_update)

    return user, False
