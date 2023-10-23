import validators as _v
from rest_framework import serializers

from autotasks.models import AutomatedTask
from scripts.models import Script
from scripts.serializers import ScriptCheckSerializer
from tacticalrmm.constants import CheckType

from .models import Check, CheckHistory, CheckResult


class AssignedTaskField(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"


class CheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckResult
        fields = "__all__"


class CheckSerializer(serializers.ModelSerializer):
    readable_desc = serializers.ReadOnlyField()
    assignedtasks = AssignedTaskField(many=True, read_only=True)
    alert_template = serializers.SerializerMethodField()
    check_result = serializers.SerializerMethodField()

    def get_check_result(self, obj):
        return (
            CheckResultSerializer(obj.check_result).data
            if isinstance(obj.check_result, CheckResult)
            else {}
        )

    def get_alert_template(self, obj):
        if obj.agent:
            alert_template = obj.agent.alert_template
        else:
            alert_template = None

        if not alert_template:
            return None

        return {
            "name": alert_template.name,
            "always_email": alert_template.check_always_email,
            "always_text": alert_template.check_always_text,
            "always_alert": alert_template.check_always_alert,
        }

    class Meta:
        model = Check
        fields = "__all__"

    # https://www.django-rest-framework.org/api-guide/serializers/#object-level-validation
    def validate(self, val):
        try:
            check_type = val["check_type"]
            filter = (
                {"agent": val["agent"]}
                if "agent" in val.keys()
                else {"policy": val["policy"]}
            )
        except KeyError:
            return val

        # disk checks
        # make sure no duplicate diskchecks exist for an agent/policy
        if check_type == CheckType.DISK_SPACE:
            if not self.instance:  # only on create
                checks = Check.objects.filter(**filter).filter(
                    check_type=CheckType.DISK_SPACE
                )
                for check in checks:
                    if val["disk"] in check.disk:
                        raise serializers.ValidationError(
                            f"A disk check for Drive {val['disk']} already exists!"
                        )

            if not val["warning_threshold"] and not val["error_threshold"]:
                raise serializers.ValidationError(
                    "Warning threshold or Error Threshold must be set"
                )

            if (
                val["warning_threshold"] < val["error_threshold"]
                and val["warning_threshold"] > 0
                and val["error_threshold"] > 0
            ):
                raise serializers.ValidationError(
                    "Warning threshold must be greater than Error Threshold"
                )

        # ping checks
        if check_type == CheckType.PING:
            if (
                not _v.ipv4(val["ip"])
                and not _v.ipv6(val["ip"])
                and not _v.domain(val["ip"])
            ):
                raise serializers.ValidationError(
                    "Please enter a valid IP address or domain name"
                )

        if check_type == CheckType.CPU_LOAD and not self.instance:
            if Check.objects.filter(**filter, check_type=CheckType.CPU_LOAD).exists():
                raise serializers.ValidationError(
                    "A cpuload check for this agent already exists"
                )

            if not val["warning_threshold"] and not val["error_threshold"]:
                raise serializers.ValidationError(
                    "Warning threshold or Error Threshold must be set"
                )

            if (
                val["warning_threshold"] > val["error_threshold"]
                and val["warning_threshold"] > 0
                and val["error_threshold"] > 0
            ):
                raise serializers.ValidationError(
                    "Warning threshold must be less than Error Threshold"
                )

        if check_type == CheckType.MEMORY and not self.instance:
            if Check.objects.filter(**filter, check_type=CheckType.MEMORY).exists():
                raise serializers.ValidationError(
                    "A memory check for this agent already exists"
                )

            if not val["warning_threshold"] and not val["error_threshold"]:
                raise serializers.ValidationError(
                    "Warning threshold or Error Threshold must be set"
                )

            if (
                val["warning_threshold"] > val["error_threshold"]
                and val["warning_threshold"] > 0
                and val["error_threshold"] > 0
            ):
                raise serializers.ValidationError(
                    "Warning threshold must be less than Error Threshold"
                )

        return val


class AssignedTaskCheckRunnerField(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = ["id", "enabled"]


class CheckRunnerGetSerializer(serializers.ModelSerializer):
    # only send data needed for agent to run a check
    script = ScriptCheckSerializer(read_only=True)
    script_args = serializers.SerializerMethodField()
    env_vars = serializers.SerializerMethodField()

    def get_script_args(self, obj):
        if obj.check_type != CheckType.SCRIPT:
            return []

        agent = self.context["agent"] if "agent" in self.context.keys() else obj.agent
        return Script.parse_script_args(
            agent=agent, shell=obj.script.shell, args=obj.script_args
        )

    def get_env_vars(self, obj):
        if obj.check_type != CheckType.SCRIPT:
            return []

        agent = self.context["agent"] if "agent" in self.context.keys() else obj.agent

        return Script.parse_script_env_vars(
            agent=agent,
            shell=obj.script.shell,
            env_vars=obj.env_vars
            or obj.script.env_vars,  # check's env_vars override the script's env vars
        )

    class Meta:
        model = Check
        exclude = [
            "policy",
            "overridden_by_policy",
            "name",
            "email_alert",
            "text_alert",
            "fails_b4_alert",
            "svc_display_name",
            "svc_policy_mode",
            "created_by",
            "created_time",
            "modified_by",
            "modified_time",
            "dashboard_alert",
        ]


class CheckHistorySerializer(serializers.ModelSerializer):
    # used for return large amounts of graph data
    class Meta:
        model = CheckHistory
        fields = ("x", "y", "results")


class CheckAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = "__all__"
