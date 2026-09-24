from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User


class TelegramAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "organization",
        )
        read_only_fields = fields

    def get_organization(self, obj: User) -> dict[str, str] | None:
        if obj.organization_id is None:
            return None
        return {
            "id": str(obj.organization_id),
            "name": obj.organization.name,
            "slug": obj.organization.slug,
        }
