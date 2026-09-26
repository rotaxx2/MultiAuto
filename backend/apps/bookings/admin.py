from django.contrib import admin

from .models import Booking, BookingReminder


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("start_at", "end_at", "status", "branch", "client", "service", "car", "workstation", "price")
    search_fields = ("client__username", "car__license_plate", "car__brand", "car__model", "service__name", "branch__name")
    list_filter = ("status", "organization", "branch", "service")
    ordering = ("-start_at",)
    autocomplete_fields = ("organization", "branch", "client", "car", "service", "workstation")


@admin.register(BookingReminder)
class BookingReminderAdmin(admin.ModelAdmin):
    list_display = ("booking", "kind", "scheduled_at", "sent_at", "created_at")
    list_filter = ("kind", "sent_at")
    search_fields = ("booking__client__username", "booking__car__license_plate")
    autocomplete_fields = ("booking",)
