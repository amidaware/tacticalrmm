from rest_framework import serializers

from .models import AutomatedTask
from agents.models import Agent

from scripts.serializers import ScriptSerializer


class TaskSerializer(serializers.ModelSerializer):

    assigned_check = serializers.ReadOnlyField()
    schedule = serializers.ReadOnlyField()

    class Meta:
        model = AutomatedTask
        fields = "__all__"
        depth = 1


class AgentTaskSerializer(serializers.ModelSerializer):

    script = ScriptSerializer(read_only=True)

    class Meta:
        model = AutomatedTask
        fields = (
            "timeout",
            "script",
        )


class AutoTaskSerializer(serializers.ModelSerializer):

    autotasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = (
            "pk",
            "hostname",
            "autotasks",
        )
