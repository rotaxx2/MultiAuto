from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminOrOwner
from apps.services.models import Service
from apps.services.serializers import ServiceSerializer
from apps.telegram_bot.permissions import IsClient

from .models import Branch
from .serializers import AdminBranchSerializer, BranchSerializer


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


class AdminBranchViewSet(ModelViewSet):
    serializer_class = AdminBranchSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.user.organization).order_by("name")

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
