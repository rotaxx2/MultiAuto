from rest_framework import serializers

from .models import User


class AdminClientSerializer(serializers.ModelSerializer):
    cars_count = serializers.IntegerField(read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "cars_count",
            "bookings_count",
            "date_joined",
            "created_at",
            "is_active",
        )
        read_only_fields = fields
