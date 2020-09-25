import requests
from time import sleep
from loguru import logger

from django.conf import settings
from django.db import IntegrityError
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

from tacticalrmm.utils import notify_error

logger.configure(**settings.LOG_CONFIG)


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def trigger_patch_scan(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
    reboot_policy = agent.get_patch_policy().reboot_after_install
    reboot = False

    if reboot_policy == "always":
        reboot = True

    if request.data["reboot"]:
        if reboot_policy == "required":
            reboot = True
        elif reboot_policy == "never":
            agent.needs_reboot = True
            agent.save(update_fields=["needs_reboot"])

    if reboot:
        r = agent.salt_api_cmd(
            timeout=15,
            func="system.reboot",
            arg=7,
            kwargs={"in_seconds": True},
        )

        if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
            check_for_updates_task.apply_async(
                queue="wupdate", kwargs={"pk": agent.pk, "wait": False}
            )
        else:
            logger.info(f"{agent.hostname} is rebooting after updates were installed.")
    else:
        check_for_updates_task.apply_async(
            queue="wupdate", kwargs={"pk": agent.pk, "wait": False}
        )

    return Response("ok")


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

        agent.salt_id = f"{agent.hostname}-{agent.pk}"
        agent.save(update_fields=["salt_id"])

        if agent.monitoring_type == "workstation":
            WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
        else:
            WinUpdatePolicy(agent=agent).save()

        # Generate policies for new agent
        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        return Response({"pk": agent.pk})
    else:
        return Response("err", status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def update(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

    if agent.update_pending and request.data["version"] != agent.version:
        agent.update_pending = False
        agent.save(update_fields=["update_pending"])

    serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(last_seen=djangotime.now())

    sync_salt_modules_task.delay(agent.pk)
    get_installed_software.delay(agent.pk)
    get_wmi_detail_task.delay(agent.pk)
    check_for_updates_task.apply_async(
        queue="wupdate", kwargs={"pk": agent.pk, "wait": True}
    )

    if not agent.choco_installed:
        install_chocolatey.delay(agent.pk, wait=True)

    return Response("ok")


@api_view(["POST"])
def on_agent_first_install(request):
    pk = request.data["pk"]
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=20, func="saltutil.sync_modules")

    if r == "timeout" or r == "error" or not r:
        return notify_error("err")

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

    recovery = agent.recoveryactions.filter(last_run=None).last()
    if recovery is not None:
        recovery.last_run = djangotime.now()
        recovery.save(update_fields=["last_run"])
        return Response(recovery.send())

    # get any pending actions
    if agent.pendingactions.filter(status="pending").count() > 0:
        agent.handle_pending_actions()

    return Response("ok")


class CheckRunner(APIView):
    """
    For windows agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
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


class SaltInfo(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        ret = {
            "latestVer": settings.LATEST_SALT_VER,
            "currentVer": agent.salt_ver,
            "salt_id": agent.salt_id,
        }
        return Response(ret)

    def patch(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        agent.salt_ver = request.data["ver"]
        agent.salt_update_pending = False
        agent.save(update_fields=["salt_ver", "salt_update_pending"])
        return Response("ok")


class MeshInfo(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        return Response(agent.mesh_node_id)

    def patch(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        agent.mesh_node_id = request.data["nodeidhex"]
        agent.save(update_fields=["mesh_node_id"])
        return Response("ok")
