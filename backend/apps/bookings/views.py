from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.branches.models import Branch
from apps.services.models import Service
from apps.services.views import IsAdminOrOwner
from apps.telegram_bot.permissions import IsClient

from .models import Booking
from .serializers import AdminBookingUpdateSerializer, BookingCreateSerializer, BookingSerializer
from .services.availability_service import get_allowed_booking_dates, get_available_slots
from .services.booking_service import cancel_client_booking


class MyBookingViewSet(ReadOnlyModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsClient]

    def get_queryset(self):
        return Booking.objects.filter(client=self.request.user).select_related("branch", "car", "service")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        try:
            booking = cancel_client_booking(booking=booking, client=request.user)
        except DjangoValidationError as exc:
            return Response({"error": {"code": "BOOKING_CANCEL_INVALID", "message": str(exc.message), "details": {}}}, status=400)
        return Response(BookingSerializer(booking).data)


class BookingCreateView(APIView):
    permission_classes = [IsClient]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BranchAvailabilityView(APIView):
    permission_classes = [IsClient]

    def get(self, request, branch_id):
        raw_date = request.query_params.get("date")
        service_id = request.query_params.get("service_id")
        if not raw_date or not service_id:
            return Response({"error": {"code": "INVALID_REQUEST", "message": "date and service_id are required.", "details": {}}}, status=400)

        branch = get_object_or_404(Branch.objects.filter(organization=request.user.organization, is_active=True), id=branch_id)
        service = get_object_or_404(
            Service.objects.filter(organization=request.user.organization, is_active=True),
            id=service_id,
        )
        try:
            target_date = date.fromisoformat(raw_date)
        except ValueError:
            return Response({"error": {"code": "INVALID_DATE", "message": "date must use YYYY-MM-DD format.", "details": {}}}, status=400)

        slots = get_available_slots(branch, service, target_date)
        return Response(
            {
                "date": target_date.isoformat(),
                "timezone": branch.timezone,
                "service_id": str(service.id),
                "duration_minutes": service.duration_minutes,
                "slots": [
                    {
                        "start_at": slot.start_at.isoformat(),
                        "end_at": slot.end_at.isoformat(),
                        "total_workstations": slot.total_workstations,
                        "occupied_workstations": slot.occupied_workstations,
                        "free_workstations": slot.free_workstations,
                        "is_available": slot.is_available,
                    }
                    for slot in slots
                ],
            }
        )


class BranchAvailableDatesView(APIView):
    permission_classes = [IsClient]

    def get(self, request, branch_id):
        branch = get_object_or_404(Branch.objects.filter(organization=request.user.organization, is_active=True), id=branch_id)
        return Response(
            {
                "timezone": branch.timezone,
                "dates": [
                    {
                        "date": item.date.isoformat(),
                        "label": item.label,
                        "is_available": item.is_available,
                    }
                    for item in get_allowed_booking_dates(branch)
                ],
            }
        )


class AdminBookingViewSet(ModelViewSet):
    permission_classes = [IsAdminOrOwner]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Booking.objects.filter(organization=self.request.user.organization).select_related("branch", "car", "service", "client")

    def get_serializer_class(self):
        if self.action in {"partial_update", "update"}:
            return AdminBookingUpdateSerializer
        return BookingSerializer
