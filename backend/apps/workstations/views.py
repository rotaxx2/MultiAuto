from rest_framework.viewsets import ModelViewSet

from apps.services.views import IsAdminOrOwner

from .models import Workstation
from .serializers import WorkstationSerializer


class AdminWorkstationViewSet(ModelViewSet):
    serializer_class = WorkstationSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        return Workstation.objects.filter(
            branch__organization=self.request.user.organization,
        ).select_related("branch", "branch__organization")
