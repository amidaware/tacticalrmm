from rest_framework import serializers

from .models import Policy
from autotasks.serializers import TaskSerializer
from checks.serializers import CheckSerializer


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class PolicyRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"
        depth = 2


class CheckPolicySerializer(serializers.ModelSerializer):

    checks = CheckSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "checks",
        )


class AutoTaskPolicySerializer(serializers.ModelSerializer):

    autotasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "autotasks",
        )
