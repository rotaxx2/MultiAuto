from django.contrib import admin

from .models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "phone", "is_active", "created_at")
    search_fields = ("name", "organization__name", "address", "phone")
    list_filter = ("is_active", "organization")
    ordering = ("organization__name", "name")
    autocomplete_fields = ("organization",)
