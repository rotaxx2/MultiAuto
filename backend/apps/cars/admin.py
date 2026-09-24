from django.contrib import admin

from .models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("brand", "model", "license_plate", "color", "owner", "created_at")
    search_fields = ("brand", "model", "license_plate", "color", "owner__username", "owner__telegram_id")
    list_filter = ("brand", "color", "created_at")
    ordering = ("brand", "model")
    autocomplete_fields = ("owner",)
