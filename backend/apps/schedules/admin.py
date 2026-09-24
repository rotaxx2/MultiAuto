from django.contrib import admin

from .models import BusinessHour, ScheduleException


@admin.register(BusinessHour)
class BusinessHourAdmin(admin.ModelAdmin):
    list_display = ("branch", "weekday", "opening_time", "closing_time", "is_closed")
    search_fields = ("branch__name", "branch__organization__name")
    list_filter = ("weekday", "is_closed", "branch__organization")
    ordering = ("branch__organization__name", "branch__name", "weekday")
    autocomplete_fields = ("branch",)


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ("branch", "date", "opening_time", "closing_time", "is_closed", "reason")
    search_fields = ("branch__name", "branch__organization__name", "reason")
    list_filter = ("is_closed", "date", "branch__organization")
    ordering = ("branch__organization__name", "branch__name", "date")
    autocomplete_fields = ("branch",)
