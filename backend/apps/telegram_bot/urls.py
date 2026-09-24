from django.urls import path

from .views import MeView, MyBookingsView, MyCarsView, MyProfileView, TelegramAuthView

urlpatterns = [
    path("v1/client/auth/telegram", TelegramAuthView.as_view(), name="client-telegram-auth"),
    path("v1/client/me", MeView.as_view(), name="client-me-versioned"),
    path("me/", MeView.as_view(), name="client-me"),
    path("my-profile/", MyProfileView.as_view(), name="client-my-profile"),
    path("my-cars/", MyCarsView.as_view(), name="client-my-cars"),
    path("my-bookings/", MyBookingsView.as_view(), name="client-my-bookings"),
]
