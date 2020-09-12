import os
from time import sleep

import requests
from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from loguru import logger
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from agents.models import Agent, AgentOutage
from agents.serializers import AgentSerializer, WinAgentSerializer
from agents.tasks import (
    agent_recovery_email_task,
    get_wmi_detail_task,
    sync_salt_modules_task,
)
from autotasks.models import AutomatedTask
from autotasks.serializers import TaskRunnerGetSerializer, TaskRunnerPatchSerializer
from checks.models import Check
from checks.serializers import CheckResultsSerializer, CheckRunnerGetSerializer
from clients.models import Client, Site
from software.tasks import get_installed_software, install_chocolatey
from tacticalrmm.utils import notify_error
from winupdate.models import WinUpdate, WinUpdatePolicy
from winupdate.tasks import check_for_updates_task

logger.configure(**settings.LOG_CONFIG)


class NewAgent(APIView):
    """ For the installer """

    def post(self, request):
        """
        Creates and returns the agents auth token
        which is stored in the agent's local db
        and used to authenticate every agent request
        """

        if "agent_id" not in request.data:
            return notify_error("Invalid payload")

        agentid = request.data["agent_id"]
        if Agent.objects.filter(agent_id=agentid).exists():
            return notify_error(
                "Agent already exists. Remove old agent first if trying to re-install"
            )

        user = User.objects.create_user(
            username=agentid, password=User.objects.make_random_password(60)
        )
        token = Token.objects.create(user=user)
        return Response({"token": token.key})

    def patch(self, request):
        """ Creates the agent """

        if Agent.objects.filter(agent_id=request.data["agent_id"]).exists():
            return notify_error(
                "Agent already exists. Remove old agent first if trying to re-install"
            )

        client = get_object_or_404(Client, pk=int(request.data["client"]))
        site = get_object_or_404(Site, pk=int(request.data["site"]))

        agent = Agent(
            agent_id=request.data["agent_id"],
            hostname=request.data["hostname"],
            client=client.client,
            site=site.site,
            monitoring_type=request.data["monitoring_type"],
            description=request.data["description"],
            mesh_node_id=request.data["mesh_node_id"],
            last_seen=djangotime.now(),
        )
        agent.save()
        agent.salt_id = f"{agent.hostname}-{agent.pk}"
        agent.save(update_fields=["salt_id"])

        if agent.monitoring_type == "workstation":
            WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
        else:
            WinUpdatePolicy(agent=agent).save()

        # Generate policies for new agent
        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        return Response({"pk": agent.pk, "saltid": f"{agent.hostname}-{agent.pk}"})


class MeshExe(APIView):
    """ Sends the mesh exe to the installer """

    def post(self, request):
        exe = "meshagent.exe" if request.data["arch"] == "64" else "meshagent-x86.exe"
        mesh_exe = os.path.join(settings.EXE_DIR, exe)

        if not os.path.exists(mesh_exe):
            return notify_error("Mesh Agent executable not found")

        if settings.DEBUG:
            with open(mesh_exe, "rb") as f:
                response = HttpResponse(
                    f.read(),
                    content_type="application/vnd.microsoft.portable-executable",
                )
                response["Content-Disposition"] = f"inline; filename={exe}"
                return response
        else:
            response = HttpResponse()
            response["Content-Disposition"] = f"attachment; filename={exe}"
            response["X-Accel-Redirect"] = f"/private/exe/{exe}"
            return response


class SaltMinion(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        ret = {
            "latestVer": settings.LATEST_SALT_VER,
            "currentVer": agent.salt_ver,
            "salt_id": agent.salt_id,
        }
        return Response(ret)

    def post(self, request):
        # accept the salt key
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if agent.salt_id != request.data["saltid"]:
            return notify_error("Salt keys do not match")

        try:
            resp = requests.post(
                f"http://{settings.SALT_HOST}:8123/run",
                json=[
                    {
                        "client": "wheel",
                        "fun": "key.accept",
                        "match": request.data["saltid"],
                        "username": settings.SALT_USERNAME,
                        "password": settings.SALT_PASSWORD,
                        "eauth": "pam",
                    }
                ],
                timeout=30,
            )
        except Exception:
            return notify_error("No communication between agent and salt-api")

        try:
            data = resp.json()["return"][0]["data"]
            minion = data["return"]["minions"][0]
        except Exception:
            return notify_error("Key error")

        if data["success"] and minion == request.data["saltid"]:
            return Response("Salt key was accepted")
        else:
            return notify_error("Not accepted")

    def patch(self, request):
        # sync modules
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        r = agent.salt_api_cmd(timeout=20, func="saltutil.sync_modules")

        if r == "timeout" or r == "error" or not r:
            return notify_error("Failed to sync salt modules")

        return Response("Successfully synced salt modules")

    def put(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        agent.salt_ver = request.data["ver"]
        agent.salt_update_pending = False
        agent.save(update_fields=["salt_ver", "salt_update_pending"])
        return Response("ok")
