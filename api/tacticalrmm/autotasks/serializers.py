from rest_framework import serializers

from scripts.models import Script

from .models import AutomatedTask


class TaskSerializer(serializers.ModelSerializer):

    check_name = serializers.ReadOnlyField(source="assigned_check.readable_desc")
    schedule = serializers.ReadOnlyField()
    last_run = serializers.ReadOnlyField(source="last_run_as_timezone")
    alert_template = serializers.SerializerMethodField()
    run_time_date = serializers.DateTimeField(format="iso-8601")
    expire_date = serializers.DateTimeField(format="iso-8601", allow_null=True)

    def validate(self, data):

        # run_time_date required
        if (
            data["task_type"] in ["runonce", "daily", "weekly", "monthly", "monthlydow"]
            and not data["run_time_date"]
        ):
            raise serializers.ValidationError(
                f"run_time_date is required for task_type '{data['task_type']}'"
            )

        # daily task type validation
        if data["task_type"] == "daily":
            if not data["daily_interval"]:
                raise serializers.ValidationError(
                    f"daily_interval is required for task_type '{data['task_type']}'"
                )

        # weekly task type validation
        if data["task_type"] == "weekly":
            if not data["weekly_interval"]:
                raise serializers.ValidationError(
                    f"weekly_interval is required for task_type '{data['task_type']}'"
                )

            if not data["run_time_bit_weekdays"]:
                raise serializers.ValidationError(
                    f"run_time_bit_weekdays is required for task_type '{data['task_type']}'"
                )

        # monthly task type validation
        if data["task_type"] == "monthly":
            if not data["monthly_months_of_year"]:
                raise serializers.ValidationError(
                    f"monthly_months_of_year is required for task_type '{data['task_type']}'"
                )

            if not data["monthly_days_of_month"]:
                raise serializers.ValidationError(
                    f"monthly_days_of_month is required for task_type '{data['task_type']}'"
                )

        # monthly day of week task type validation
        if data["task_type"] == "monthlydow":
            if not data["monthly_months_of_year"]:
                raise serializers.ValidationError(
                    f"monthly_months_of_year is required for task_type '{data['task_type']}'"
                )

            if not data["monthly_weeks_of_month"]:
                raise serializers.ValidationError(
                    f"monthly_weeks_of_month is required for task_type '{data['task_type']}'"
                )

            if not data["run_time_bit_weekdays"]:
                raise serializers.ValidationError(
                    f"run_time_bit_weekdays is required for task_type '{data['task_type']}'"
                )

        # check failure task type validation
        if data["task_type"] == "checkfailure":
            if not data["assigned_check"]:
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


class TaskGOGetSerializer(serializers.ModelSerializer):
    task_actions = serializers.SerializerMethodField()

    def get_task_actions(self, obj):
        tmp = []
        for action in obj.actions:
            if action["type"] == "cmd":
                tmp.append(
                    {
                        "type": "cmd",
                        "command": Script.parse_script_args(
                            agent=obj.agent,
                            shell=action["shell"],
                            args=[action["command"]],
                        )[0],
                        "shell": action["shell"],
                        "timeout": action["timeout"],
                    }
                )
            elif action["type"] == "script":
                script = Script.objects.get(pk=action["script"])
                tmp.append(
                    {
                        "type": "script",
                        "script_name": script.name,
                        "code": script.code,
                        "script_args": Script.parse_script_args(
                            agent=obj.agent,
                            shell=script.shell,
                            args=action["script_args"],
                        ),
                        "shell": script.shell,
                        "timeout": action["timeout"],
                    }
                )
        return tmp

    class Meta:
        model = AutomatedTask
        fields = ["id", "continue_on_error", "enabled", "task_actions"]


class TaskRunnerPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"


class TaskAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = "__all__"
