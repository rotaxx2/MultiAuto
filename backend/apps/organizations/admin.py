from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "phone", "email", "is_active", "created_at")
    search_fields = ("name", "slug", "phone", "email", "address")
    list_filter = ("is_active", "created_at")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
