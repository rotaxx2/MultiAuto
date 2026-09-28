from django.db.models import Count
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminOrOwner

from .models import User, UserRole
from .serializers import AdminClientSerializer


class AdminClientViewSet(ReadOnlyModelViewSet):
    serializer_class = AdminClientSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return (
            User.objects.filter(
                organization=self.request.user.organization,
                role=UserRole.CLIENT,
            )
            .annotate(cars_count=Count("cars", distinct=True), bookings_count=Count("bookings", distinct=True))
            .order_by("-created_at")
        )
