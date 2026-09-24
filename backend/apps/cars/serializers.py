from __future__ import annotations

from rest_framework import serializers

from .models import Car, normalize_license_plate


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ("id", "brand", "model", "license_plate", "color", "year", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_brand(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Brand is required.")
        return value.strip()

    def validate_model(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Model is required.")
        return value.strip()

    def validate_license_plate(self, value: str) -> str:
        normalized = normalize_license_plate(value)
        if not normalized:
            raise serializers.ValidationError("License plate is required.")
        return normalized

    def validate(self, attrs: dict) -> dict:
        owner = self.context["request"].user
        license_plate = attrs.get("license_plate", getattr(self.instance, "license_plate", ""))
        qs = Car.objects.filter(owner=owner, license_plate=normalize_license_plate(license_plate))
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError({"license_plate": "Car with this license plate already exists."})
        return attrs

    def create(self, validated_data: dict) -> Car:
        return Car.objects.create(owner=self.context["request"].user, **validated_data)
