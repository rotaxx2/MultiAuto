from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.models import UserRole
from apps.telegram_bot.permissions import IsClient

from .models import Service
from .serializers import ServiceSerializer


class ClientServiceViewSet(ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsClient]

    def get_queryset(self):
        return Service.objects.filter(
            organization=self.request.user.organization,
            is_active=True,
        ).order_by("name")


class IsAdminOrOwner(IsAuthenticated):
    def has_permission(self, request, view) -> bool:
        return bool(
            super().has_permission(request, view)
            and request.user.is_active
            and request.user.role in {UserRole.ADMIN, UserRole.OWNER}
            and request.user.organization_id
        )


class AdminServiceViewSet(ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return Service.objects.filter(organization=self.request.user.organization).order_by("name")

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
