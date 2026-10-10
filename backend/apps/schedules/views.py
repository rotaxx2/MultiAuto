from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.branches.models import Branch
from apps.accounts.permissions import IsAdminOrOwner
from apps.telegram_bot.permissions import IsClient

from .models import BusinessHour, ScheduleException
from .serializers import BusinessHourSerializer, ScheduleExceptionSerializer
from .services import get_branch_schedule


class AdminBusinessHourViewSet(ModelViewSet):
    serializer_class = BusinessHourSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return BusinessHour.objects.filter(branch__organization=self.request.user.organization)


class AdminScheduleExceptionViewSet(ModelViewSet):
    serializer_class = ScheduleExceptionSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return ScheduleException.objects.filter(branch__organization=self.request.user.organization)


class ClientBranchScheduleView(APIView):
    permission_classes = [IsClient]

    def get(self, request, pk):
        branch = get_object_or_404(
            Branch.objects.filter(organization=request.user.organization, is_active=True),
            pk=pk,
        )
        raw_date = request.query_params.get("date")
        try:
            target_date = date.fromisoformat(raw_date) if raw_date else timezone.localdate()
        except ValueError:
            return Response(
                {"error": {"code": "INVALID_DATE", "message": "date must use YYYY-MM-DD format.", "details": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        schedule = get_branch_schedule(branch, target_date)
        return Response(
            {
                "branch": str(branch.id),
                "date": target_date.isoformat(),
                "is_closed": schedule.is_closed,
                "opening_time": schedule.opening_time.isoformat(timespec="minutes") if schedule.opening_time else None,
                "closing_time": schedule.closing_time.isoformat(timespec="minutes") if schedule.closing_time else None,
                "source": schedule.source,
                "reason": schedule.reason,
            }
        )
