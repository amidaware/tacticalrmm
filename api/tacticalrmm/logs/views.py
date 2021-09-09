import asyncio
from datetime import datetime as dt

from accounts.models import User
from accounts.serializers import UserSerializer
from agents.models import Agent
from agents.serializers import AgentHostnameSerializer
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tacticalrmm.utils import notify_error, get_default_timezone

from .models import AuditLog, PendingAction, DebugLog
from .permissions import AuditLogPerms, DebugLogPerms, ManagePendingActionPerms
from .serializers import AuditLogSerializer, DebugLogSerializer, PendingActionSerializer


class GetAuditLogs(APIView):
    permission_classes = [IsAuthenticated, AuditLogPerms]

    def patch(self, request):
        from agents.models import Agent
        from clients.models import Client

        pagination = request.data["pagination"]

        order_by = (
            f"-{pagination['sortBy']}"
            if pagination["descending"]
            else f"{pagination['sortBy']}"
        )

        agentFilter = Q()
        clientFilter = Q()
        actionFilter = Q()
        objectFilter = Q()
        userFilter = Q()
        timeFilter = Q()

        if "agentFilter" in request.data:
            agentFilter = Q(agent_id__in=request.data["agentFilter"])

        elif "clientFilter" in request.data:
            clients = Client.objects.filter(
                pk__in=request.data["clientFilter"]
            ).values_list("id")
            agents = Agent.objects.filter(site__client_id__in=clients).values_list(
                "hostname"
            )
            clientFilter = Q(agent__in=agents)

        if "userFilter" in request.data:
            userFilter = Q(username__in=request.data["userFilter"])

        if "actionFilter" in request.data:
            actionFilter = Q(action__in=request.data["actionFilter"])

        if "objectFilter" in request.data:
            objectFilter = Q(object_type__in=request.data["objectFilter"])

        if "timeFilter" in request.data:
            timeFilter = Q(
                entry_time__lte=djangotime.make_aware(dt.today()),
                entry_time__gt=djangotime.make_aware(dt.today())
                - djangotime.timedelta(days=request.data["timeFilter"]),
            )

        audit_logs = (
            AuditLog.objects.filter(agentFilter | clientFilter)
            .filter(userFilter)
            .filter(actionFilter)
            .filter(objectFilter)
            .filter(timeFilter)
        ).order_by(order_by)

        paginator = Paginator(audit_logs, pagination["rowsPerPage"])
        ctx = {"default_tz": get_default_timezone()}

        return Response(
            {
                "audit_logs": AuditLogSerializer(
                    paginator.get_page(pagination["page"]), many=True, context=ctx
                ).data,
                "total": paginator.count,
            }
        )


class PendingActions(APIView):
    permission_classes = [IsAuthenticated, ManagePendingActionPerms]

    def patch(self, request):
        status_filter = "completed" if request.data["showCompleted"] else "pending"
        if "agentPK" in request.data.keys():
            actions = PendingAction.objects.filter(
                agent__pk=request.data["agentPK"], status=status_filter
            )
            total = PendingAction.objects.filter(
                agent__pk=request.data["agentPK"]
            ).count()
            completed = PendingAction.objects.filter(
                agent__pk=request.data["agentPK"], status="completed"
            ).count()

        else:
            actions = PendingAction.objects.filter(status=status_filter).select_related(
                "agent"
            )
            total = PendingAction.objects.count()
            completed = PendingAction.objects.filter(status="completed").count()

        ret = {
            "actions": PendingActionSerializer(actions, many=True).data,
            "completed_count": completed,
            "total": total,
        }
        return Response(ret)

    def delete(self, request):
        action = get_object_or_404(PendingAction, pk=request.data["pk"])
        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": action.details["taskname"]},
        }
        r = asyncio.run(action.agent.nats_cmd(nats_data, timeout=10))
        if r != "ok":
            return notify_error(r)

        action.delete()
        return Response(f"{action.agent.hostname}: {action.description} was cancelled")


class GetDebugLog(APIView):
    permission_classes = [IsAuthenticated, DebugLogPerms]

    def patch(self, request):
        agentFilter = Q()
        logTypeFilter = Q()
        logLevelFilter = Q()

        if "logTypeFilter" in request.data:
            logTypeFilter = Q(log_type=request.data["logTypeFilter"])

        if "logLevelFilter" in request.data:
            logLevelFilter = Q(log_level=request.data["logLevelFilter"])

        if "agentFilter" in request.data:
            agentFilter = Q(agent=request.data["agentFilter"])

        debug_logs = (
            DebugLog.objects.prefetch_related("agent")
            .filter(logLevelFilter)
            .filter(agentFilter)
            .filter(logTypeFilter)
        )

        ctx = {"default_tz": get_default_timezone()}
        ret = DebugLogSerializer(debug_logs, many=True, context=ctx).data
        return Response(ret)
