from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.branches.models import Branch
from apps.cars.models import Car
from apps.services.models import Service
from apps.workstations.models import Workstation

from .models import Booking, BookingStatus
from .services.booking_service import create_booking, update_admin_booking


class BookingSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    client_name = serializers.SerializerMethodField()
    client_telegram_id = serializers.IntegerField(source="client.telegram_id", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    workstation_name = serializers.CharField(source="workstation.name", read_only=True)
    car_label = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "branch",
            "branch_name",
            "client",
            "client_name",
            "client_telegram_id",
            "car",
            "car_label",
            "service",
            "service_name",
            "workstation",
            "workstation_name",
            "start_at",
            "end_at",
            "status",
            "price",
            "client_comment",
            "admin_comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_car_label(self, obj: Booking) -> str:
        return f"{obj.car.brand} {obj.car.model} {obj.car.license_plate}"

    def get_client_name(self, obj: Booking) -> str:
        return obj.client.get_full_name() or obj.client.username or str(obj.client.telegram_id or obj.client_id)


class BookingCreateSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    car_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    start_at = serializers.DateTimeField()
    client_comment = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data: dict) -> Booking:
        request = self.context["request"]
        branch = Branch.objects.get(id=validated_data["branch_id"])
        car = Car.objects.get(id=validated_data["car_id"])
        service = Service.objects.get(id=validated_data["service_id"])
        try:
            return create_booking(
                client=request.user,
                branch=branch,
                car=car,
                service=service,
                start_at=validated_data["start_at"],
                client_comment=validated_data.get("client_comment", ""),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(str(exc.message)) from exc

    def validate(self, attrs: dict) -> dict:
        for model, field in ((Branch, "branch_id"), (Car, "car_id"), (Service, "service_id")):
            if not model.objects.filter(id=attrs[field]).exists():
                raise serializers.ValidationError({field: "Object not found."})
        return attrs


class AdminBookingUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=BookingStatus.choices, required=False)
    admin_comment = serializers.CharField(required=False, allow_blank=True)
    start_at = serializers.DateTimeField(required=False)
    workstation = serializers.PrimaryKeyRelatedField(queryset=Workstation.objects.all(), required=False)

    class Meta:
        model = Booking
        fields = ("status", "admin_comment", "start_at", "workstation")

    def validate_workstation(self, workstation: Workstation) -> Workstation:
        user = self.context["request"].user
        if workstation.branch.organization_id != user.organization_id:
            raise serializers.ValidationError("Workstation does not belong to your organization.")
        return workstation

    def update(self, instance: Booking, validated_data: dict) -> Booking:
        try:
            return update_admin_booking(
                booking=instance,
                status=validated_data.get("status"),
                admin_comment=validated_data.get("admin_comment") if "admin_comment" in validated_data else None,
                start_at=validated_data.get("start_at") if "start_at" in validated_data else None,
                workstation=validated_data.get("workstation") if "workstation" in validated_data else None,
            )
        except (DjangoValidationError, ValueError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
