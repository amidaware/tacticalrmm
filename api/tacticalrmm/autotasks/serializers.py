from datetime import datetime

from django.utils import timezone as djangotime
from rest_framework import serializers
from django.conf import settings

from scripts.models import Script
from tacticalrmm.constants import TaskType

from .models import AutomatedTask, TaskResult


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = "__all__"
        read_only_fields = ("agent", "task")


class TaskSerializer(serializers.ModelSerializer):
    check_name = serializers.ReadOnlyField(source="assigned_check.readable_desc")
    schedule = serializers.ReadOnlyField()
    alert_template = serializers.SerializerMethodField()
    run_time_date = serializers.DateTimeField(required=False)
    expire_date = serializers.DateTimeField(allow_null=True, required=False)
    task_result = serializers.SerializerMethodField()

    def get_task_result(self, obj):
        return (
            TaskResultSerializer(obj.task_result).data
            if isinstance(obj.task_result, TaskResult)
            else {}
        )

    def validate_actions(self, value):
        if not value:
            raise serializers.ValidationError(
                "There must be at least one action configured"
            )

        for action in value:
            if "type" not in action:
                raise serializers.ValidationError(
                    "Each action must have a type field of either 'script' or 'cmd'"
                )

            if action["type"] == "script":
                if "script" not in action:
                    raise serializers.ValidationError(
                        "A script action type must have a 'script' field with primary key of script"
                    )

                if "script_args" not in action:
                    raise serializers.ValidationError(
                        "A script action type must have a 'script_args' field with an array of arguments"
                    )

                if "timeout" not in action:
                    raise serializers.ValidationError(
                        "A script action type must have a 'timeout' field"
                    )

            if action["type"] == "cmd":
                if "command" not in action:
                    raise serializers.ValidationError(
                        "A command action type must have a 'command' field"
                    )

                if "timeout" not in action:
                    raise serializers.ValidationError(
                        "A command action type must have a 'timeout' field"
                    )

        return value

    def validate(self, data):
        # allow editing with task_type not specified
        if self.instance and "task_type" not in data:
            # remove schedule related fields from data
            if "run_time_date" in data:
                del data["run_time_date"]
            if "expire_date" in data:
                del data["expire_date"]
            if "daily_interval" in data:
                del data["daily_interval"]
            if "weekly_interval" in data:
                del data["weekly_interval"]
            if "run_time_bit_weekdays" in data:
                del data["run_time_bit_weekdays"]
            if "monthly_months_of_year" in data:
                del data["monthly_months_of_year"]
            if "monthly_days_of_month" in data:
                del data["monthly_days_of_month"]
            if "monthly_weeks_of_month" in data:
                del data["monthly_weeks_of_month"]
            if "assigned_check" in data:
                del data["assigned_check"]
            return data

        if (
            "expire_date" in data
            and isinstance(data["expire_date"], datetime)
            and djangotime.now() > data["expire_date"]
        ):
            raise serializers.ValidationError("Expires date/time is in the past")

        # run_time_date required
        if (
            data["task_type"]
            in (
                TaskType.RUN_ONCE,
                TaskType.DAILY,
                TaskType.WEEKLY,
                TaskType.MONTHLY,
                TaskType.MONTHLY_DOW,
            )
            and not data["run_time_date"]
        ):
            raise serializers.ValidationError(
                f"run_time_date is required for task_type '{data['task_type']}'"
            )

        # daily task type validation
        if data["task_type"] == TaskType.DAILY:
            if "daily_interval" not in data or not data["daily_interval"]:
                raise serializers.ValidationError(
                    f"daily_interval is required for task_type '{data['task_type']}'"
                )

        # weekly task type validation
        elif data["task_type"] == TaskType.WEEKLY:
            if "weekly_interval" not in data or not data["weekly_interval"]:
                raise serializers.ValidationError(
                    f"weekly_interval is required for task_type '{data['task_type']}'"
                )

            if "run_time_bit_weekdays" not in data or not data["run_time_bit_weekdays"]:
                raise serializers.ValidationError(
                    f"run_time_bit_weekdays is required for task_type '{data['task_type']}'"
                )

        # monthly task type validation
        elif data["task_type"] == TaskType.MONTHLY:
            if (
                "monthly_months_of_year" not in data
                or not data["monthly_months_of_year"]
            ):
                raise serializers.ValidationError(
                    f"monthly_months_of_year is required for task_type '{data['task_type']}'"
                )

            if "monthly_days_of_month" not in data or not data["monthly_days_of_month"]:
                raise serializers.ValidationError(
                    f"monthly_days_of_month is required for task_type '{data['task_type']}'"
                )

        # monthly day of week task type validation
        elif data["task_type"] == TaskType.MONTHLY_DOW:
            if (
                "monthly_months_of_year" not in data
                or not data["monthly_months_of_year"]
            ):
                raise serializers.ValidationError(
                    f"monthly_months_of_year is required for task_type '{data['task_type']}'"
                )

            if (
                "monthly_weeks_of_month" not in data
                or not data["monthly_weeks_of_month"]
            ):
                raise serializers.ValidationError(
                    f"monthly_weeks_of_month is required for task_type '{data['task_type']}'"
                )

            if "run_time_bit_weekdays" not in data or not data["run_time_bit_weekdays"]:
                raise serializers.ValidationError(
                    f"run_time_bit_weekdays is required for task_type '{data['task_type']}'"
                )

        # check failure task type validation
        elif data["task_type"] == TaskType.CHECK_FAILURE:
            if "assigned_check" not in data or not data["assigned_check"]:
                raise serializers.ValidationError(
                    f"assigned_check is required for task_type '{data['task_type']}'"
                )

        return data

    def get_alert_template(self, obj):
        if obj.agent:
            alert_template = obj.agent.alert_template
        else:
            alert_template = None

        if not alert_template:
            return None
        return {
            "name": alert_template.name,
            "always_email": alert_template.task_always_email,
            "always_text": alert_template.task_always_text,
            "always_alert": alert_template.task_always_alert,
        }

    class Meta:
        model = AutomatedTask
        fields = "__all__"


class TaskGOGetSerializer(serializers.ModelSerializer):
    task_actions = serializers.SerializerMethodField()

    def get_task_actions(self, obj):
        tmp = []
        actions_to_remove = []
        agent = self.context["agent"]
        for action in obj.actions:
            if action["type"] == "cmd":
                tmp.append(
                    {
                        "type": "cmd",
                        "command": Script.parse_script_args(
                            agent=agent,
                            shell=action["shell"],
                            args=[action["command"]],
                        )[0],
                        "shell": action["shell"],
                        "timeout": action["timeout"],
                    }
                )
            elif action["type"] == "script":
                try:
                    script = Script.objects.get(pk=action["script"])
                except Script.DoesNotExist:
                    # script doesn't exist so remove it
                    actions_to_remove.append(action["script"])
                    continue
                # wrote a custom migration for env_vars but leaving this just in case.
                # can be removed later
                try:
                    env_vars = action["env_vars"]
                except KeyError:
                    env_vars = []
                tmp.append(
                    {
                        "type": "script",
                        "script_name": script.name,
                        "code": script.code,
                        "script_args": Script.parse_script_args(
                            agent=agent,
                            shell=script.shell,
                            args=action["script_args"],
                        ),
                        "shell": script.shell,
                        "timeout": action["timeout"],
                        "run_as_user": script.run_as_user,
                        "env_vars": Script.parse_script_env_vars(
                            agent=agent,
                            shell=script.shell,
                            env_vars=env_vars,
                        ),
                        "nushell_enable_config": settings.NUSHELL_ENABLE_CONFIG,
                        "deno_default_permissions": settings.DENO_DEFAULT_PERMISSIONS,
                    }
                )
        if actions_to_remove:
            task = AutomatedTask.objects.get(pk=obj.pk)
            task.actions = [
                action
                for action in task.actions
                if action["type"] == "cmd"
                or (
                    "script" in action.keys()
                    and action["script"] not in actions_to_remove
                )
            ]
            task.save(update_fields=["actions"])
        return tmp

    class Meta:
        model = AutomatedTask
        fields = ["id", "continue_on_error", "enabled", "task_actions"]


class TaskAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"
