from rest_framework import serializers

from apps.branches.models import Branch

from .models import Workstation


class WorkstationSerializer(serializers.ModelSerializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())

    class Meta:
        model = Workstation
        fields = ("id", "branch", "name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_branch(self, branch: Branch) -> Branch:
        user = self.context["request"].user
        if branch.organization_id != user.organization_id:
            raise serializers.ValidationError("Branch does not belong to your organization.")
        return branch

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()
