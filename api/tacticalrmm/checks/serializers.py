import validators as _v

from rest_framework import serializers

from .models import Check
from scripts.serializers import ScriptSerializer


class CheckSerializer(serializers.ModelSerializer):

    readable_desc = serializers.ReadOnlyField()
    script = ScriptSerializer(read_only=True)

    class Meta:
        model = Check
        fields = "__all__"

    def validate_ip(self, val):
        if not _v.ipv4(val) and not _v.ipv6(val) and not _v.domain(val):
            raise serializers.ValidationError(
                "Please enter a valid IP address or domain name"
            )
        return val


""" class PolicyChecksSerializer(serializers.ModelSerializer):
    diskchecks = DiskCheckSerializer(many=True, read_only=True)
    cpuloadchecks = CpuLoadCheckSerializer(many=True, read_only=True)
    memchecks = MemCheckSerializer(many=True, read_only=True)
    pingchecks = PingCheckSerializer(many=True, read_only=True)
    winservicechecks = WinServiceCheckSerializer(many=True, read_only=True)
    scriptchecks = ScriptCheckSerializer(many=True, read_only=True)
    eventlogchecks = EventLogCheckSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "active",
            "diskchecks",
            "cpuloadchecks",
            "memchecks",
            "pingchecks",
            "winservicechecks",
            "scriptchecks",
            "eventlogchecks",
        )
 """
