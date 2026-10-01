"""Root URL configuration for MultiAuto."""

from django.contrib import admin
from django.urls import include, path

from .health import celery_health, health

urlpatterns = [
    path("health/", health),
    path("health/celery/", celery_health),
    path("admin/", admin.site.urls),
    path("api/", include("apps.telegram_bot.urls")),
]
