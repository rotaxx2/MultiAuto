from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "telegram_id", "role", "organization", "is_active", "is_staff", "created_at")
    search_fields = ("username", "first_name", "last_name", "telegram_id", "phone_number", "organization__name")
    list_filter = ("role", "is_active", "is_staff", "organization", "created_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("organization",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "MultiAuto",
            {
                "fields": (
                    "telegram_id",
                    "phone_number",
                    "role",
                    "organization",
                )
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "MultiAuto",
            {
                "fields": (
                    "telegram_id",
                    "phone_number",
                    "role",
                    "organization",
                )
            },
        ),
    )
