from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.services.models import Service
from apps.services.serializers import ServiceSerializer
from apps.telegram_bot.permissions import IsClient

from .models import Branch
from .serializers import BranchSerializer


class ClientBranchViewSet(ReadOnlyModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsClient]

    def get_queryset(self):
        return Branch.objects.filter(
            organization=self.request.user.organization,
            is_active=True,
        ).order_by("name")


class ClientBranchServiceViewSet(ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsClient]

    def get_queryset(self):
        branch_id = self.kwargs["branch_pk"]
        branch_exists = Branch.objects.filter(
            id=branch_id,
            organization=self.request.user.organization,
            is_active=True,
        ).exists()
        if not branch_exists:
            return Service.objects.none()
        return Service.objects.filter(
            organization=self.request.user.organization,
            is_active=True,
        ).order_by("name")
