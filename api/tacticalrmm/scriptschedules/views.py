import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from agents.models import Agent
from autotasks.models import AutomatedTask, TaskResult
from scripts.models import Script

from .models import OpenframeScriptSchedule
from .serializers import (
    OpenframeAgentAssignmentSerializer,
    OpenframeAssignedAgentSerializer,
    OpenframeExecutionHistorySerializer,
    OpenframeScriptScheduleCreateSerializer,
    OpenframeScriptScheduleDetailSerializer,
    OpenframeScriptScheduleListSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CRUD — /script-schedules/
# =============================================================================


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def openframe_script_schedule_list_create(request):
    """
    GET  /script-schedules/   — list all schedules
    POST /script-schedules/   — create a new schedule (+ underlying AutomatedTask)
    """
    if request.method == "GET":
        schedules = (
            OpenframeScriptSchedule.objects.select_related("managed_task")
            .prefetch_related("assigned_agents")
            .all()
        )
        return Response(
            OpenframeScriptScheduleListSerializer(schedules, many=True).data
        )

    # POST: create AutomatedTask + OpenframeScriptSchedule
    serializer = OpenframeScriptScheduleCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    schedule = serializer.save()
    return Response(
        OpenframeScriptScheduleDetailSerializer(schedule).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def openframe_script_schedule_detail(request, pk):
    """
    GET    /script-schedules/<pk>/   — full detail (task fields + agents + history)
    PUT    /script-schedules/<pk>/   — partial update (modifies AutomatedTask fields)
    DELETE /script-schedules/<pk>/   — delete schedule + task + all TaskResults
    """
    schedule = get_object_or_404(
        OpenframeScriptSchedule.objects.select_related("managed_task").prefetch_related(
            "assigned_agents", "assigned_agents__site", "assigned_agents__site__client"
        ),
        pk=pk,
    )

    if request.method == "GET":
        return Response(OpenframeScriptScheduleDetailSerializer(schedule).data)

    if request.method == "PUT":
        serializer = OpenframeScriptScheduleCreateSerializer(
            schedule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        return Response(OpenframeScriptScheduleDetailSerializer(schedule).data)

    # DELETE — cascades: schedule → task → task_results
    schedule.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Agent management — /script-schedules/<pk>/agents/
# =============================================================================


@api_view(["GET", "PUT", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def openframe_script_schedule_agents(request, pk):
    """
    GET    — list assigned agents
    PUT    — replace entire agent set
    POST   — add agents to the set
    DELETE — remove agents from the set

    Body for PUT/POST/DELETE: {"agents": ["agent-id-1", "agent-id-2"]}

    After any mutation, TaskResult rows are synced:
    - New rows created for newly-assigned agents
    - Stale rows deleted for removed agents
    """
    schedule = get_object_or_404(
        OpenframeScriptSchedule.objects.select_related("managed_task"),
        pk=pk,
    )

    if request.method == "GET":
        agents = schedule.assigned_agents.select_related("site", "site__client")
        return Response(OpenframeAssignedAgentSerializer(agents, many=True).data)

    serializer = OpenframeAgentAssignmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    agent_ids = serializer.validated_data["agents"]
    agents = Agent.objects.filter(agent_id__in=agent_ids)

    if request.method == "PUT":
        schedule.assigned_agents.set(agents)
    elif request.method == "POST":
        schedule.assigned_agents.add(*agents)
    elif request.method == "DELETE":
        schedule.assigned_agents.remove(*agents)

    # Sync TaskResult rows after mutation
    sync_result = schedule.sync_task_results()

    return Response(
        {
            "agents_count": schedule.assigned_agents.count(),
            "task_results_created": sync_result["created"],
            "task_results_deleted": sync_result["deleted"],
        }
    )


# =============================================================================
# Execution History — /script-schedules/<pk>/history/
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def openframe_script_schedule_history(request, pk):
    """
    GET /script-schedules/<pk>/history/?limit=50&offset=0

    Paginated execution results across all agents.
    """
    schedule = get_object_or_404(
        OpenframeScriptSchedule.objects.select_related("managed_task"),
        pk=pk,
    )

    if not schedule.managed_task_id:
        return Response({"total": 0, "results": []})

    results_qs = (
        TaskResult.objects.filter(
            task=schedule.managed_task,
            last_run__isnull=False,
        )
        .select_related("agent", "agent__site", "agent__site__client")
        .order_by("-last_run")
    )

    limit = min(int(request.query_params.get("limit", 50)), 200)
    offset = int(request.query_params.get("offset", 0))
    page = results_qs[offset : offset + limit]

    return Response(
        {
            "total": results_qs.count(),
            "limit": limit,
            "offset": offset,
            "results": OpenframeExecutionHistorySerializer(page, many=True).data,
        }
    )


# =============================================================================
# Reverse lookups
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def openframe_schedules_for_script(request, script_pk):
    """
    GET /scripts/<script_pk>/schedules/

    Returns all OpenframeScriptSchedules whose managed_task.actions
    reference this script's PK. Used on the Script Detail page to show
    "Which schedules use this script?"
    """
    script = get_object_or_404(Script, pk=script_pk)

    # JSONField lookup: find AutomatedTasks whose actions list contains
    # at least one entry with {"script": <pk>}
    task_ids = list(
        AutomatedTask.objects.filter(
            actions__contains=[{"script": script.pk}]
        ).values_list("pk", flat=True)
    )

    schedules = (
        OpenframeScriptSchedule.objects.filter(managed_task_id__in=task_ids)
        .select_related("managed_task")
        .prefetch_related("assigned_agents")
    )

    data = []
    for s in schedules:
        t = s.managed_task
        data.append(
            {
                "id": s.pk,
                "name": t.name,
                "task_type": t.task_type,
                "run_time_date": t.run_time_date,
                "enabled": t.enabled,
                "agents_count": s.assigned_agents.count(),
            }
        )

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def openframe_schedules_for_agent(request, agent_id):
    """
    GET /agents/<agent_id>/script-schedules/

    Returns all OpenframeScriptSchedules assigned to this agent.
    Used on the Agent Detail page.
    """
    agent = get_object_or_404(Agent, agent_id=agent_id)
    schedules = agent.openframe_script_schedules.select_related("managed_task")

    data = []
    for s in schedules:
        t = s.managed_task
        data.append(
            {
                "id": s.pk,
                "managed_task_id": t.pk,
                "name": t.name,
                "task_type": t.task_type,
                "run_time_date": t.run_time_date,
                "enabled": t.enabled,
                "actions": t.actions,
                "task_supported_platforms": t.task_supported_platforms,
            }
        )

    return Response(data)
