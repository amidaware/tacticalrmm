import subprocess

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone as djangotime
from django.db.models import Q
from datetime import datetime as dt

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView

from .models import PendingAction, AuditLog
from agents.models import Agent
from accounts.models import User
from .serializers import PendingActionSerializer, AuditLogSerializer
from agents.serializers import AgentHostnameSerializer
from accounts.serializers import UserSerializer
from .tasks import cancel_pending_action_task


class GetAuditLogs(APIView):
    def patch(self, request):
        from clients.models import Client
        from agents.models import Agent

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
        )

        return Response(AuditLogSerializer(audit_logs, many=True).data)


class FilterOptionsAuditLog(APIView):
    def post(self, request):
        if request.data["type"] == "agent":
            agents = Agent.objects.filter(hostname__icontains=request.data["pattern"])
            return Response(AgentHostnameSerializer(agents, many=True).data)

        if request.data["type"] == "user":
            users = User.objects.filter(
                username__icontains=request.data["pattern"], agent=None
            )
            return Response(UserSerializer(users, many=True).data)

        return Response("error", status=status.HTTP_400_BAD_REQUEST)


@api_view()
def agent_pending_actions(request, pk):
    action = PendingAction.objects.filter(agent__pk=pk)
    return Response(PendingActionSerializer(action, many=True).data)


@api_view()
def all_pending_actions(request):
    actions = PendingAction.objects.all()
    return Response(PendingActionSerializer(actions, many=True).data)


@api_view(["DELETE"])
def cancel_pending_action(request):
    action = get_object_or_404(PendingAction, pk=request.data["pk"])
    data = PendingActionSerializer(action).data
    cancel_pending_action_task.delay(data)
    action.delete()
    return Response(
        f"{action.agent.hostname}: {action.description} will be cancelled shortly"
    )


@api_view()
def debug_log(request, mode, hostname, order):
    log_file = settings.LOG_CONFIG["handlers"][0]["sink"]

    agents = Agent.objects.all()
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
