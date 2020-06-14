import requests

import os
from time import sleep
from loguru import logger

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from agents.models import Agent, AgentOutage
from accounts.models import User
from checks.models import Check
from autotasks.models import AutomatedTask
from winupdate.models import WinUpdate, WinUpdatePolicy

from agents.tasks import (
    sync_salt_modules_task,
    get_wmi_detail_task,
    agent_recovery_email_task,
)
from clients.models import Client, Site

from winupdate.tasks import check_for_updates_task
from agents.serializers import (
    AgentSerializer,
    WinAgentSerializer,
)
from autotasks.serializers import TaskRunnerGetSerializer, TaskRunnerPatchSerializer
from checks.serializers import CheckRunnerGetSerializer, CheckResultsSerializer
from software.tasks import install_chocolatey, get_installed_software

logger.configure(**settings.LOG_CONFIG)


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def trigger_patch_scan(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
    check_for_updates_task.delay(agent.pk, wait=False)

    if request.data["reboot"]:
        agent.needs_reboot = True
    else:
        agent.needs_reboot = False

    agent.save(update_fields=["needs_reboot"])
    return Response("ok")


@api_view(["POST"])
def get_mesh_exe(request):
    mesh_exe = os.path.join(settings.EXE_DIR, "meshagent.exe")
    if not os.path.exists(mesh_exe):
        return Response("error", status=status.HTTP_400_BAD_REQUEST)
    if settings.DEBUG:
        with open(mesh_exe, "rb") as f:
            response = HttpResponse(
                f.read(), content_type="application/vnd.microsoft.portable-executable"
            )
            response["Content-Disposition"] = "inline; filename=meshagent.exe"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = "attachment; filename=meshagent.exe"
        response["X-Accel-Redirect"] = "/private/exe/meshagent.exe"
        return response


@api_view(["POST"])
def create_auth_token(request):
    try:
        agentid = request.data["agent_id"]
    except Exception:
        logger.error("agentid was not provided with request")
        return Response({"error": "bad data"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            user = User.objects.create_user(
                username=agentid, password=User.objects.make_random_password(50)
            )
        except IntegrityError:
            user = User.objects.get(username=agentid)
            token = Token.objects.get(user=user)
            return Response({"token": token.key})

    try:
        user = User.objects.get(username=agentid)
    except Exception:
        return Response({"error": "bad user"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        token = Token.objects.create(user=user)
        return Response({"token": token.key})


@api_view(["POST"])
def accept_salt_key(request):
    saltid = request.data["saltid"]
    try:
        resp = requests.post(
            "http://" + settings.SALT_HOST + ":8123/run",
            json=[
                {
                    "client": "wheel",
                    "fun": "key.accept",
                    "match": saltid,
                    "username": settings.SALT_USERNAME,
                    "password": settings.SALT_PASSWORD,
                    "eauth": "pam",
                }
            ],
            timeout=30,
        )
    except Exception:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            data = resp.json()["return"][0]["data"]
            minion = data["return"]["minions"][0]
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            if data["success"] and minion == saltid:
                return Response("accepted")
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def add(request):
    data = request.data

    client = get_object_or_404(Client, pk=int(data["client"]))
    site = get_object_or_404(Site, pk=int(data["site"]))

    if not Agent.objects.filter(agent_id=data["agent_id"]).exists():
        agent = Agent(
            agent_id=data["agent_id"],
            hostname=data["hostname"],
            client=client.client,
            site=site.site,
            monitoring_type=data["monitoring_type"],
            description=data["description"],
            mesh_node_id=data["mesh_node_id"],
            last_seen=djangotime.now(),
        )

        agent.save()

        if agent.monitoring_type == "workstation":
            WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
        else:
            WinUpdatePolicy(agent=agent).save()

        return Response({"pk": agent.pk})
    else:
        return Response("err", status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def update(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
    serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(last_seen=djangotime.now())

    sync_salt_modules_task.delay(agent.pk)
    get_installed_software.delay(agent.pk)
    get_wmi_detail_task.delay(agent.pk)

    if not agent.choco_installed:
        install_chocolatey.delay(agent.pk, wait=True)

    return Response("ok")


@api_view(["POST"])
def on_agent_first_install(request):
    pk = request.data["pk"]
    agent = get_object_or_404(Agent, pk=pk)

    resp = agent.salt_api_cmd(
        hostname=agent.salt_id, timeout=60, func="saltutil.sync_modules"
    )
    try:
        data = resp.json()
    except Exception:
        return Response("err", status=status.HTTP_400_BAD_REQUEST)

    try:
        ret = data["return"][0][agent.salt_id]
    except KeyError:
        return Response("err", status=status.HTTP_400_BAD_REQUEST)

    if not data["return"][0][agent.salt_id]:
        return Response("err", status=status.HTTP_400_BAD_REQUEST)

    get_wmi_detail_task.delay(agent.pk)
    get_installed_software.delay(agent.pk)
    check_for_updates_task.delay(agent.pk, wait=True)
    return Response("ok")


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def hello(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

    serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(last_seen=djangotime.now())

    outages = AgentOutage.objects.filter(agent=agent)

    if outages.exists() and outages.last().is_active:
        last_outage = outages.last()
        last_outage.recovery_time = djangotime.now()
        last_outage.save(update_fields=["recovery_time"])

        if agent.overdue_email_alert:
            agent_recovery_email_task.delay(pk=last_outage.pk)
        if agent.overdue_text_alert:
            # TODO
            pass

    return Response("ok")


class CheckRunner(APIView):
    """
    For windows agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)

        if agent.policies_pending:
            agent.generate_checks_from_policies()

        checks = Check.objects.filter(agent__pk=pk, overriden_by_policy=False)

        ret = {
            "agent": agent.pk,
            "check_interval": agent.check_interval,
            "checks": CheckRunnerGetSerializer(checks, many=True).data,
        }
        return Response(ret)

    def patch(self, request, pk):
        check = get_object_or_404(Check, pk=pk)

        if check.check_type != "cpuload" and check.check_type != "memory":
            serializer = CheckResultsSerializer(
                instance=check, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(last_run=djangotime.now())

        else:
            check.last_run = djangotime.now()
            check.save(update_fields=["last_run"])

        check.handle_check(request.data)

        return Response("ok")


class TaskRunner(APIView):
    """
    For windows agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        task = get_object_or_404(AutomatedTask, pk=pk)
        return Response(TaskRunnerGetSerializer(task).data)

    def patch(self, request, pk):
        task = get_object_or_404(AutomatedTask, pk=pk)

        serializer = TaskRunnerPatchSerializer(
            instance=task, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(last_run=djangotime.now())
        return Response("ok")
