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

    # https://www.django-rest-framework.org/api-guide/serializers/#object-level-validation
    def validate(self, val):
        try:
            check_type = val["check_type"]
        except KeyError:
            return val
        # disk checks
        # make sure no duplicate diskchecks exist for an agent/policy
        if check_type == "diskspace" and not self.instance:  # only on create
            checks = Check.objects.filter(**self.context)
            if checks:
                for check in checks:
                    if val["disk"] in check.disk:
                        raise serializers.ValidationError(
                            f"A disk check for Drive {val['disk']} already exists!"
                        )

        # ping checks
        if check_type == "ping":
            if (
                not _v.ipv4(val["ip"])
                and not _v.ipv6(val["ip"])
                and not _v.domain(val["ip"])
            ):
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
