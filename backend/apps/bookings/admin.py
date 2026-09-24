from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("start_at", "end_at", "status", "branch", "service", "car", "workstation", "price")
    search_fields = ("car__license_plate", "car__brand", "car__model", "service__name", "branch__name")
    list_filter = ("status", "organization", "branch", "service")
    ordering = ("-start_at",)
    autocomplete_fields = ("organization", "branch", "client", "car", "service", "workstation")
