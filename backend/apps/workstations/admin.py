from django.contrib import admin

from .models import Workstation


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "is_active", "created_at")
    search_fields = ("name", "branch__name", "branch__organization__name")
    list_filter = ("is_active", "branch__organization", "branch")
    ordering = ("branch__organization__name", "branch__name", "name")
    autocomplete_fields = ("branch",)
