import asyncio
import subprocess
from datetime import datetime as dt

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import UserSerializer
from agents.models import Agent
from agents.serializers import AgentHostnameSerializer
from tacticalrmm.utils import notify_error

from .models import AuditLog, PendingAction
from .permissions import AuditLogPerms, DebugLogPerms, ManagePendingActionPerms
from .serializers import AuditLogSerializer, PendingActionSerializer


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
            agentFilter = Q(agent__in=request.data["agentFilter"])

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

        return Response(
            {
                "audit_logs": AuditLogSerializer(
                    paginator.get_page(pagination["page"]), many=True
                ).data,
                "total": paginator.count,
            }
        )


class FilterOptionsAuditLog(APIView):
    permission_classes = [IsAuthenticated, AuditLogPerms]

    def post(self, request):
        if request.data["type"] == "agent":
            agents = Agent.objects.filter(hostname__icontains=request.data["pattern"])
            return Response(AgentHostnameSerializer(agents, many=True).data)

        if request.data["type"] == "user":
            users = User.objects.filter(
                username__icontains=request.data["pattern"],
                agent=None,
                is_installer_user=False,
            )
            return Response(UserSerializer(users, many=True).data)

        return Response("error", status=status.HTTP_400_BAD_REQUEST)


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


@api_view()
@permission_classes([IsAuthenticated, DebugLogPerms])
def debug_log(request, mode, hostname, order):
    log_file = settings.LOG_CONFIG["handlers"][0]["sink"]

    agents = Agent.objects.prefetch_related("site").only("pk", "hostname")
    agent_hostnames = AgentHostnameSerializer(agents, many=True)

    switch_mode = {
        "info": "INFO",
        "critical": "CRITICAL",
        "error": "ERROR",
        "warning": "WARNING",
    }
    level = switch_mode.get(mode, "INFO")

    if hostname == "all" and order == "latest":
        cmd = f"grep -h {level} {log_file} | tac"
    elif hostname == "all" and order == "oldest":
        cmd = f"grep -h {level} {log_file}"
    elif hostname != "all" and order == "latest":
        cmd = f"grep {hostname} {log_file} | grep -h {level} | tac"
    elif hostname != "all" and order == "oldest":
        cmd = f"grep {hostname} {log_file} | grep -h {level}"
    else:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)

    contents = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=True,
    )

    if not contents.stdout:
        resp = f"No {mode} logs"
    else:
        resp = contents.stdout

    return Response({"log": resp, "agents": agent_hostnames.data})


@api_view()
@permission_classes([IsAuthenticated, DebugLogPerms])
def download_log(request):
    log_file = settings.LOG_CONFIG["handlers"][0]["sink"]
    if settings.DEBUG:
        with open(log_file, "rb") as f:
            response = HttpResponse(f.read(), content_type="text/plain")
            response["Content-Disposition"] = "attachment; filename=debug.log"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = "attachment; filename=debug.log"
        response["X-Accel-Redirect"] = "/private/log/debug.log"
        return response
