from rest_framework.viewsets import ModelViewSet

from apps.telegram_bot.permissions import IsClient

from .models import Car
from .serializers import CarSerializer


class MyCarViewSet(ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsClient]

    def get_queryset(self):
        return Car.objects.filter(owner=self.request.user).order_by("brand", "model")
