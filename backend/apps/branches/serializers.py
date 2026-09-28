from rest_framework import serializers

from .models import Branch


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "address", "phone", "timezone", "is_active", "created_at", "updated_at")
        read_only_fields = fields


class AdminBranchSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Branch
        fields = ("id", "organization", "name", "address", "phone", "timezone", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()
