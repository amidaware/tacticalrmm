from rest_framework import serializers

from .models import (
    DiskCheck,
    CpuLoadCheck,
    MemCheck,
    PingCheck,
    WinServiceCheck,
    Script,
    ScriptCheck,
)
from agents.models import Agent


class DiskCheckSerializer(serializers.ModelSerializer):
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

    class Meta:
        model = DiskCheck
        fields = "__all__"


class CpuLoadCheckSerializer(serializers.ModelSerializer):
    more_info = serializers.ReadOnlyField()
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

    class Meta:
        model = CpuLoadCheck
        fields = "__all__"


class MemCheckSerializer(serializers.ModelSerializer):
    more_info = serializers.ReadOnlyField()
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

    class Meta:
        model = MemCheck
        fields = "__all__"


class PingCheckSerializer(serializers.ModelSerializer):
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

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
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

    class Meta:
        model = ScriptCheck
        fields = "__all__"


class WinServiceCheckSerializer(serializers.ModelSerializer):
    readable_desc = serializers.ReadOnlyField()
    assigned_task = serializers.ReadOnlyField()

    class Meta:
        model = WinServiceCheck
        fields = "__all__"


class CheckSerializer(serializers.ModelSerializer):
    diskchecks = DiskCheckSerializer(many=True, read_only=True)
    cpuloadchecks = CpuLoadCheckSerializer(many=True, read_only=True)
    memchecks = MemCheckSerializer(many=True, read_only=True)
    pingchecks = PingCheckSerializer(many=True, read_only=True)
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
            "winservicechecks",
            "scriptchecks",
        )
