from rest_framework import serializers

from .models import (
    DiskCheck,
    CpuLoadCheck,
    MemCheck,
    PingCheck,
    CpuHistory,
    WinServiceCheck,
    Script,
    ScriptCheck,
)
from agents.models import Agent
from agents.serializers import AgentSerializer


class DiskCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiskCheck
        fields = "__all__"


class CpuLoadCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = CpuLoadCheck
        fields = "__all__"


class CpuHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CpuHistory
        fields = ("cpu_history",)


class MemCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemCheck
        fields = "__all__"


class PingCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = PingCheck
        fields = "__all__"


class ScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Script
        fields = (
            "id",
            "name",
            "description",
            "filename",
            "shell",
            "filepath",
        )


class ScriptCheckSerializer(serializers.ModelSerializer):

    script = ScriptSerializer(read_only=True)

    class Meta:
        model = ScriptCheck
        fields = (
            "id",
            "check_type",
            "timeout",
            "failures",
            "status",
            "failure_count",
            "email_alert",
            "text_alert",
            "stdout",
            "stderr",
            "retcode",
            "execution_time",
            "last_run",
            "agent",
            "script",
        )


class WinServiceCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinServiceCheck
        fields = "__all__"


class CheckSerializer(serializers.ModelSerializer):
    diskchecks = DiskCheckSerializer(many=True, read_only=True)
    cpuloadchecks = CpuLoadCheckSerializer(many=True, read_only=True)
    memchecks = MemCheckSerializer(many=True, read_only=True)
    pingchecks = PingCheckSerializer(many=True, read_only=True)
    cpuhistory = CpuHistorySerializer(many=True, read_only=True)
    winservicechecks = WinServiceCheckSerializer(many=True, read_only=True)
    scriptchecks = ScriptCheckSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = (
            "hostname",
            "pk",
            "disks",
            "check_interval",
            "diskchecks",
            "cpuloadchecks",
            "memchecks",
            "pingchecks",
            "cpuhistory",
            "winservicechecks",
            "scriptchecks",
        )
