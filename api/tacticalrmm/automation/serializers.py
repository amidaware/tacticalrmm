from rest_framework import serializers

from .models import Policy, AutomatedTask
from agents.models import Agent
from checks.serializers import ScriptSerializer

class PolicySerializer(serializers.ModelSerializer):

    class Meta:
        model = Policy
        fields = "__all__"

class PolicyRelationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Policy
        fields = "__all__"
        depth = 2


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
        fields = ("timeout", "script",)

class AutoTaskSerializer(serializers.ModelSerializer):

    autotasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = (
            "pk",
            "hostname",
            "autotasks",
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
