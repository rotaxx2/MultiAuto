from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import validate_telegram_init_data
from .permissions import IsClient
from .serializers import TelegramAuthSerializer, UserProfileSerializer
from .services import TelegramUserData, get_or_create_client_from_telegram, resolve_organization


class TelegramAuthView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            telegram_data = validate_telegram_init_data(serializer.validated_data["init_data"])
        except DjangoValidationError as exc:
            return Response(
                {"error": {"code": "TELEGRAM_AUTH_INVALID", "message": str(exc.message), "details": {}}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        organization = resolve_organization(request.data.get("start_param", ""))
        user, _created = get_or_create_client_from_telegram(
            TelegramUserData(
                telegram_id=telegram_data.telegram_id,
                username=telegram_data.username,
                first_name=telegram_data.first_name,
                last_name=telegram_data.last_name,
            ),
            organization,
        )
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": UserProfileSerializer(user).data,
            }
        )


class MeView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)


class MyProfileView(MeView):
    pass


class MyCarsView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        return Response({"results": []})


class MyBookingsView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        return Response({"results": []})
