from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminOrOwner
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


class AdminServiceViewSet(ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return Service.objects.filter(organization=self.request.user.organization).order_by("name")

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
