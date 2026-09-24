"""Root URL configuration for MultiAuto."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.telegram_bot.urls")),
]
