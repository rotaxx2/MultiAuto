from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.branches.views import ClientBranchServiceViewSet, ClientBranchViewSet
from apps.bookings.views import AdminBookingViewSet, BookingCreateView, BranchAvailabilityView, MyBookingViewSet
from apps.cars.views import MyCarViewSet
from apps.schedules.views import AdminBusinessHourViewSet, AdminScheduleExceptionViewSet, ClientBranchScheduleView
from apps.services.views import AdminServiceViewSet, ClientServiceViewSet
from apps.workstations.views import AdminWorkstationViewSet
from .views import MeView, MyBookingsView, MyCarsView, MyProfileView, TelegramAuthView

router = DefaultRouter()
router.register("my-cars", MyCarViewSet, basename="my-cars")
router.register("my-bookings", MyBookingViewSet, basename="my-bookings")
router.register("services", ClientServiceViewSet, basename="client-services")
router.register("branches", ClientBranchViewSet, basename="client-branches")
router.register("admin/services", AdminServiceViewSet, basename="admin-services")
router.register("admin/workstations", AdminWorkstationViewSet, basename="admin-workstations")
router.register("admin/business-hours", AdminBusinessHourViewSet, basename="admin-business-hours")
router.register("admin/schedule-exceptions", AdminScheduleExceptionViewSet, basename="admin-schedule-exceptions")
router.register("admin/bookings", AdminBookingViewSet, basename="admin-bookings")

branch_services = ClientBranchServiceViewSet.as_view({"get": "list"})

urlpatterns = [
    path("v1/client/auth/telegram", TelegramAuthView.as_view(), name="client-telegram-auth"),
    path("v1/client/me", MeView.as_view(), name="client-me-versioned"),
    path("me/", MeView.as_view(), name="client-me"),
    path("my-profile/", MyProfileView.as_view(), name="client-my-profile"),
    path("bookings/", BookingCreateView.as_view(), name="client-booking-create"),
    path("branches/<uuid:branch_id>/availability/", BranchAvailabilityView.as_view(), name="client-branch-availability"),
    path("branches/<uuid:branch_pk>/services/", branch_services, name="client-branch-services"),
    path("branches/<uuid:pk>/schedule/", ClientBranchScheduleView.as_view(), name="client-branch-schedule"),
]

urlpatterns += router.urls
