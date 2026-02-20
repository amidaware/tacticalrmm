from rest_framework import serializers

from agents.models import Agent
from autotasks.models import AutomatedTask, TaskResult
from tacticalrmm.constants import FIELDS_TRIGGER_TASK_UPDATE_AGENT, AgentPlat, TaskSyncStatus, TaskType

from .models import OpenframeScriptSchedule


# =============================================================================
# Agent serializers
# =============================================================================


class OpenframeAssignedAgentSerializer(serializers.ModelSerializer):
    """Read-only serializer for agents assigned to a schedule."""

    client_name = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "agent_id",
            "hostname",
            "plat",
            "operating_system",
            "time_zone",
            "client_name",
            "site_name",
        ]

    def get_client_name(self, obj) -> str:
        try:
            return obj.site.client.name
        except Exception:
            return ""

    def get_site_name(self, obj) -> str:
        try:
            return obj.site.name
        except Exception:
            return ""


class OpenframeAgentAssignmentSerializer(serializers.Serializer):
    """Input serializer for assigning/removing agents by agent_id strings."""

    agents = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of agent_id strings",
    )


# =============================================================================
# Execution history
# =============================================================================


class OpenframeExecutionHistorySerializer(serializers.ModelSerializer):
    """TaskResult rows for execution history views."""

    agent_id = serializers.CharField(source="agent.agent_id")
    agent_hostname = serializers.CharField(source="agent.hostname")
    agent_platform = serializers.CharField(source="agent.plat")
    organization = serializers.SerializerMethodField()

    class Meta:
        model = TaskResult
        fields = [
            "id",
            "agent_id",
            "agent_hostname",
            "agent_platform",
            "organization",
            "retcode",
            "stdout",
            "stderr",
            "execution_time",
            "last_run",
            "status",
            "sync_status",
        ]

    def get_organization(self, obj) -> str:
        try:
            return f"{obj.agent.site.client.name} / {obj.agent.site.name}"
        except Exception:
            return ""


# =============================================================================
# List serializer (lightweight, for table views)
# =============================================================================


class OpenframeScriptScheduleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    All task-related fields are proxied from managed_task.
    """

    name = serializers.CharField(source="managed_task.name", read_only=True)
    task_type = serializers.CharField(source="managed_task.task_type", read_only=True)
    run_time_date = serializers.DateTimeField(
        source="managed_task.run_time_date", read_only=True
    )
    enabled = serializers.BooleanField(source="managed_task.enabled", read_only=True)
    task_supported_platforms = serializers.ListField(
        source="managed_task.task_supported_platforms", read_only=True
    )
    actions_count = serializers.SerializerMethodField()
    agents_count = serializers.IntegerField(
        source="assigned_agents.count", read_only=True
    )

    class Meta:
        model = OpenframeScriptSchedule
        fields = [
            "id",
            "name",
            "task_type",
            "run_time_date",
            "enabled",
            "task_supported_platforms",
            "actions_count",
            "agents_count",
        ]

    def get_actions_count(self, obj) -> int:
        if obj.managed_task and obj.managed_task.actions:
            return len(obj.managed_task.actions)
        return 0


# =============================================================================
# Detail serializer (full, with agents + history)
# =============================================================================


class OpenframeScriptScheduleDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer.
    Proxies all scheduling fields from managed_task.
    Includes assigned agents and recent execution history.
    """

    # --- Proxied from managed_task ---
    managed_task_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="managed_task.name", read_only=True)
    task_type = serializers.CharField(source="managed_task.task_type", read_only=True)
    run_time_date = serializers.DateTimeField(
        source="managed_task.run_time_date", read_only=True
    )
    daily_interval = serializers.IntegerField(
        source="managed_task.daily_interval", read_only=True
    )
    weekly_interval = serializers.IntegerField(
        source="managed_task.weekly_interval", read_only=True
    )
    run_time_bit_weekdays = serializers.IntegerField(
        source="managed_task.run_time_bit_weekdays", read_only=True
    )
    monthly_days_of_month = serializers.IntegerField(
        source="managed_task.monthly_days_of_month", read_only=True
    )
    monthly_months_of_year = serializers.IntegerField(
        source="managed_task.monthly_months_of_year", read_only=True
    )
    task_supported_platforms = serializers.ListField(
        source="managed_task.task_supported_platforms", read_only=True
    )
    enabled = serializers.BooleanField(source="managed_task.enabled", read_only=True)
    actions = serializers.JSONField(source="managed_task.actions", read_only=True)

    # --- Own relations ---
    assigned_agents = OpenframeAssignedAgentSerializer(many=True, read_only=True)
    last_runs = serializers.SerializerMethodField()

    class Meta:
        model = OpenframeScriptSchedule
        fields = [
            "id",
            "managed_task_id",
            "name",
            "task_type",
            "run_time_date",
            "daily_interval",
            "weekly_interval",
            "run_time_bit_weekdays",
            "monthly_days_of_month",
            "monthly_months_of_year",
            "task_supported_platforms",
            "enabled",
            "actions",
            "assigned_agents",
            "last_runs",
        ]

    def get_last_runs(self, obj) -> list:
        if not obj.managed_task_id:
            return []
        results = (
            TaskResult.objects.filter(task=obj.managed_task, last_run__isnull=False)
            .select_related("agent", "agent__site", "agent__site__client")
            .order_by("-last_run")[:20]
        )
        return OpenframeExecutionHistorySerializer(results, many=True).data


# =============================================================================
# Create / Update serializer
# =============================================================================


TASK_TYPE_CHOICES = [
    TaskType.RUN_ONCE,
    TaskType.DAILY,
    TaskType.WEEKLY,
    TaskType.MONTHLY,
    TaskType.MONTHLY_DOW,
]


class OpenframeScriptScheduleCreateSerializer(serializers.Serializer):
    """
    Creates an AutomatedTask + OpenframeScriptSchedule in one request.
    On update, modifies the existing AutomatedTask fields.

    All fields map directly to AutomatedTask columns.
    """

    name = serializers.CharField(max_length=255)
    task_type = serializers.ChoiceField(choices=TASK_TYPE_CHOICES)
    run_time_date = serializers.DateTimeField()

    # Recurrence fields (required depending on task_type)
    daily_interval = serializers.IntegerField(required=False, allow_null=True)
    weekly_interval = serializers.IntegerField(required=False, allow_null=True)
    run_time_bit_weekdays = serializers.IntegerField(required=False, allow_null=True)
    monthly_days_of_month = serializers.IntegerField(required=False, allow_null=True)
    monthly_months_of_year = serializers.IntegerField(required=False, allow_null=True)
    monthly_weeks_of_month = serializers.IntegerField(required=False, allow_null=True)

    # Platform filter
    task_supported_platforms = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    enabled = serializers.BooleanField(default=True)

    # Script actions — list of dicts matching AutomatedTask.actions format:
    #   [{"type": "script", "script": <pk>, "name": "...", "timeout": 60,
    #     "script_args": [], "env_vars": []}]
    actions = serializers.JSONField()

    def validate(self, data):
        task_type = data.get("task_type")

        if task_type == TaskType.DAILY:
            if not data.get("daily_interval"):
                raise serializers.ValidationError(
                    {"daily_interval": "Required for daily schedule."}
                )

        elif task_type == TaskType.WEEKLY:
            if not data.get("weekly_interval"):
                raise serializers.ValidationError(
                    {"weekly_interval": "Required for weekly schedule."}
                )
            if not data.get("run_time_bit_weekdays"):
                raise serializers.ValidationError(
                    {"run_time_bit_weekdays": "Required for weekly schedule."}
                )

        elif task_type in (TaskType.MONTHLY, TaskType.MONTHLY_DOW):
            if not data.get("monthly_months_of_year"):
                raise serializers.ValidationError(
                    {"monthly_months_of_year": "Required for monthly schedule."}
                )
            if not data.get("monthly_days_of_month"):
                raise serializers.ValidationError(
                    {"monthly_days_of_month": "Required for monthly schedule."}
                )

        if not data.get("actions"):
            raise serializers.ValidationError(
                {"actions": "At least one action is required."}
            )

        return data

    def create(self, validated_data):
        task = AutomatedTask.objects.create(
            name=validated_data["name"],
            task_type=validated_data["task_type"],
            run_time_date=validated_data["run_time_date"],
            daily_interval=validated_data.get("daily_interval"),
            weekly_interval=validated_data.get("weekly_interval"),
            run_time_bit_weekdays=validated_data.get("run_time_bit_weekdays"),
            monthly_days_of_month=validated_data.get("monthly_days_of_month"),
            monthly_months_of_year=validated_data.get("monthly_months_of_year"),
            monthly_weeks_of_month=validated_data.get("monthly_weeks_of_month"),
            task_supported_platforms=validated_data.get(
                "task_supported_platforms", ["windows", "linux", "darwin"]
            ),
            enabled=validated_data.get("enabled", True),
            actions=validated_data["actions"],
            continue_on_error=True,
            alert_severity="info",
        )
        schedule = OpenframeScriptSchedule.objects.create(managed_task=task)
        return schedule

    def update(self, instance, validated_data):
        task = instance.managed_task
        updatable_fields = [
            "name",
            "task_type",
            "run_time_date",
            "daily_interval",
            "weekly_interval",
            "run_time_bit_weekdays",
            "monthly_days_of_month",
            "monthly_months_of_year",
            "monthly_weeks_of_month",
            "task_supported_platforms",
            "enabled",
            "actions",
        ]
        for field in updatable_fields:
            if field in validated_data:
                setattr(task, field, validated_data[field])
        task.save()

        if set(validated_data) & set(FIELDS_TRIGGER_TASK_UPDATE_AGENT):
            TaskResult.objects.filter(
                task=task,
                agent__plat=AgentPlat.WINDOWS,
            ).exclude(
                sync_status=TaskSyncStatus.INITIAL,
            ).update(sync_status=TaskSyncStatus.NOT_SYNCED)

        return instance
