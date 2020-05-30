from rest_framework import serializers

from .models import AutomatedTask
from agents.models import Agent
from scripts.models import Script

from scripts.serializers import ScriptSerializer
from checks.serializers import CheckSerializer


class TaskSerializer(serializers.ModelSerializer):

    assigned_check = CheckSerializer(read_only=True)
    schedule = serializers.ReadOnlyField()

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
        fields = ["id", "filepath", "shell"]


class TaskRunnerGetSerializer(serializers.ModelSerializer):

    script = TaskRunnerScriptField(read_only=True)

    class Meta:
        model = AutomatedTask
        fields = ["id", "script", "timeout", "enabled"]


class TaskRunnerPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = ["id", "stdout", "stderr", "retcode", "last_run"]
