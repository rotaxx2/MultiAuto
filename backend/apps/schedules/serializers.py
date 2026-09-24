from rest_framework import serializers

from apps.branches.models import Branch

from .models import BusinessHour, ScheduleException


class BusinessHourSerializer(serializers.ModelSerializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())

    class Meta:
        model = BusinessHour
        fields = ("id", "branch", "weekday", "opening_time", "closing_time", "is_closed", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_branch(self, branch: Branch) -> Branch:
        if branch.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Branch does not belong to your organization.")
        return branch


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())

    class Meta:
        model = ScheduleException
        fields = (
            "id",
            "branch",
            "date",
            "is_closed",
            "opening_time",
            "closing_time",
            "reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_branch(self, branch: Branch) -> Branch:
        if branch.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Branch does not belong to your organization.")
        return branch
