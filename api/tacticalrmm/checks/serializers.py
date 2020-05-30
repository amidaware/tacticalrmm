import validators as _v

from rest_framework import serializers

from .models import Check
from autotasks.models import AutomatedTask
from scripts.serializers import ScriptSerializer


class AssignedTaskField(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"


class CheckSerializer(serializers.ModelSerializer):

    readable_desc = serializers.ReadOnlyField()
    script = ScriptSerializer(read_only=True)
    assigned_task = serializers.SerializerMethodField()

    def get_assigned_task(self, obj):
        if obj.assignedtask.exists():
            task = obj.assignedtask.get()
            return AssignedTaskField(task).data

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
            checks = Check.objects.filter(**self.context).filter(check_type="diskspace")
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
