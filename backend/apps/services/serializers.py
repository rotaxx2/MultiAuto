from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "organization",
            "name",
            "description",
            "duration_minutes",
            "price",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()
