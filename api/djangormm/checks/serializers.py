from rest_framework import serializers

from .models import (
    DiskCheck, 
    CpuLoadCheck, 
    MemCheck, 
    PingCheck, 
    CpuHistory, 
    WinServiceCheck
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

    class Meta:
        model = Agent
        fields = (
            "hostname",
            "pk",
            "disks",
            "ping_check_interval",
            "diskchecks",
            "cpuloadchecks",
            "memchecks",
            "pingchecks",
            "cpuhistory",
            "winservicechecks",
        )