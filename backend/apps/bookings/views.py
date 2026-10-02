from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminOrOwner
from apps.accounts.models import UserRole
from apps.branches.models import Branch
from apps.services.models import Service
from apps.telegram_bot.permissions import IsClient
from apps.workstations.models import Workstation

from .models import BLOCKING_BOOKING_STATUSES, Booking, BookingReminder, BookingReminderStatus
from .serializers import AdminBookingReminderSerializer, AdminBookingUpdateSerializer, BookingCreateSerializer, BookingSerializer
from .services.reminder_service import reset_failed_booking_reminder
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


class AdminBookingReminderViewSet(ReadOnlyModelViewSet):
    serializer_class = AdminBookingReminderSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        queryset = (
            BookingReminder.objects.filter(booking__organization=self.request.user.organization)
            .select_related("booking__branch", "booking__car", "booking__client", "booking__service")
            .order_by("-scheduled_at")
        )
        status_filter = self.request.query_params.get("status")
        kind_filter = self.request.query_params.get("kind")
        date_filter = self.request.query_params.get("date")
        query = self.request.query_params.get("search")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if kind_filter:
            queryset = queryset.filter(kind=kind_filter)
        if date_filter:
            queryset = queryset.filter(scheduled_at__date=date_filter)
        if query:
            search_filter = (
                models.Q(booking__client__username__icontains=query)
                | models.Q(booking__client__first_name__icontains=query)
                | models.Q(booking__client__last_name__icontains=query)
                | models.Q(booking__car__license_plate__icontains=query)
                | models.Q(booking__service__name__icontains=query)
            )
            try:
                search_filter |= models.Q(booking_id=UUID(query))
            except ValueError:
                pass
            queryset = queryset.filter(search_filter)
        return queryset

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        from .tasks import send_booking_reminder_task

        reminder = self.get_object()
        booking = reminder.booking
        now = timezone.now()
        if reminder.status != BookingReminderStatus.FAILED:
            return Response({"error": {"code": "NOTIFICATION_RETRY_INVALID", "message": "Only failed notifications can be retried.", "details": {}}}, status=400)
        if reminder.sent_at:
            return Response({"error": {"code": "NOTIFICATION_ALREADY_SENT", "message": "Notification was already sent.", "details": {}}}, status=400)
        if booking.status not in BLOCKING_BOOKING_STATUSES or booking.start_at <= now:
            return Response({"error": {"code": "BOOKING_NOT_ACTIVE", "message": "Booking is no longer active for retry.", "details": {}}}, status=400)

        reset_failed_booking_reminder(reminder)
        send_booking_reminder_task.delay(str(reminder.id))
        return Response(AdminBookingReminderSerializer(reminder).data)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminOrOwner]

    def get(self, request):
        organization = request.user.organization
        now = timezone.now()
        branch = Branch.objects.filter(organization=organization, is_active=True).order_by("name").first()
        branch_tz = ZoneInfo(branch.timezone) if branch else timezone.get_current_timezone()
        today = now.astimezone(branch_tz).date()
        tomorrow = today + timedelta(days=1)
        today_start = datetime.combine(today, time.min, tzinfo=branch_tz)
        tomorrow_start = datetime.combine(tomorrow, time.min, tzinfo=branch_tz)
        day_after_tomorrow_start = tomorrow_start + timedelta(days=1)

        org_bookings = Booking.objects.filter(organization=organization)
        today_count = org_bookings.filter(start_at__gte=today_start, start_at__lt=tomorrow_start).count()
        tomorrow_count = org_bookings.filter(start_at__gte=tomorrow_start, start_at__lt=day_after_tomorrow_start).count()
        active_count = org_bookings.filter(status__in=BLOCKING_BOOKING_STATUSES).count()
        clients_count = request.user.__class__.objects.filter(organization=organization, role=UserRole.CLIENT).count()
        total_boxes = Workstation.objects.filter(branch__organization=organization, is_active=True).count()
        occupied_boxes = (
            org_bookings.filter(status__in=BLOCKING_BOOKING_STATUSES, start_at__lte=now, end_at__gt=now)
            .values("workstation_id")
            .distinct()
            .count()
        )

        upcoming = org_bookings.filter(start_at__gte=now).select_related("branch", "car", "client", "service", "workstation").order_by("start_at")[:8]
        by_status = org_bookings.values("status").annotate(count=Count("id")).order_by("status")
        reminders = BookingReminder.objects.filter(booking__organization=organization)
        sent_today = reminders.filter(sent_at__gte=today_start, sent_at__lt=tomorrow_start).count()
        failed_today = reminders.filter(status=BookingReminderStatus.FAILED, last_attempt_at__gte=today_start, last_attempt_at__lt=tomorrow_start).count()
        return Response(
            {
                "today_bookings": today_count,
                "tomorrow_bookings": tomorrow_count,
                "active_bookings": active_count,
                "clients": clients_count,
                "available_boxes": max(total_boxes - occupied_boxes, 0),
                "occupied_boxes": occupied_boxes,
                "total_boxes": total_boxes,
                "bookings_by_status": {item["status"]: item["count"] for item in by_status},
                "upcoming_bookings": BookingSerializer(upcoming, many=True).data,
                "notifications": {
                    "pending": reminders.filter(status=BookingReminderStatus.PENDING).count(),
                    "sent_today": sent_today,
                    "failed_today": failed_today,
                },
            }
        )
