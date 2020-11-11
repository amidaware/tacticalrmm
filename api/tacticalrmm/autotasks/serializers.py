import pytz
from rest_framework import serializers

from .models import AutomatedTask
from agents.models import Agent
from scripts.models import Script

from scripts.serializers import ScriptCheckSerializer
from checks.serializers import CheckSerializer


class TaskSerializer(serializers.ModelSerializer):

    assigned_check = CheckSerializer(read_only=True)
    schedule = serializers.ReadOnlyField()
    last_run = serializers.ReadOnlyField(source="last_run_as_timezone")

    class Meta:
        model = AutomatedTask
        fields = "__all__"


class AutoTaskSerializer(serializers.ModelSerializer):

    autotasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = (
            "pk",
            "hostname",
            "autotasks",
        )


# below is for the windows agent
class TaskRunnerScriptField(serializers.ModelSerializer):
    class Meta:
        model = Script
        fields = ["id", "filepath", "filename", "shell", "script_type"]


class TaskRunnerGetSerializer(serializers.ModelSerializer):

    script = TaskRunnerScriptField(read_only=True)

    class Meta:
        model = AutomatedTask
        fields = ["id", "script", "timeout", "enabled", "script_args"]


class TaskGOGetSerializer(serializers.ModelSerializer):
    script = ScriptCheckSerializer(read_only=True)

    class Meta:
        model = AutomatedTask
        fields = ["id", "script", "timeout", "enabled", "script_args"]


class TaskRunnerPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"
