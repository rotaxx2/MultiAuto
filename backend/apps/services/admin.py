from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "duration_minutes", "price", "is_active", "created_at")
    search_fields = ("name", "description", "organization__name")
    list_filter = ("is_active", "organization")
    ordering = ("organization__name", "name")
    autocomplete_fields = ("organization",)
