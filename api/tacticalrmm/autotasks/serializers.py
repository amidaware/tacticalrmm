from rest_framework import serializers

from agents.models import Agent
from checks.serializers import CheckSerializer
from scripts.models import Script
from scripts.serializers import ScriptCheckSerializer

from .models import AutomatedTask


class TaskSerializer(serializers.ModelSerializer):

    assigned_check = CheckSerializer(read_only=True)
    schedule = serializers.ReadOnlyField()
    last_run = serializers.ReadOnlyField(source="last_run_as_timezone")
    alert_template = serializers.SerializerMethodField()

    def get_alert_template(self, obj):

        if obj.agent:
            alert_template = obj.agent.alert_template
        else:
            alert_template = None

        if not alert_template:
            return None
        else:
            return {
                "name": alert_template.name,
                "always_email": alert_template.task_always_email,
                "always_text": alert_template.task_always_text,
                "always_alert": alert_template.task_always_alert,
            }

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
    script_args = serializers.SerializerMethodField()

    def get_script_args(self, obj):
        return Script.parse_script_args(
            agent=obj.agent, shell=obj.script.shell, args=obj.script_args
        )

    class Meta:
        model = AutomatedTask
        fields = ["id", "script", "timeout", "enabled", "script_args"]


class TaskRunnerPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"
