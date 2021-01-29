import asyncio
import os
import requests
from loguru import logger
from packaging import version as pyver

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from agents.models import Agent
from checks.models import Check
from autotasks.models import AutomatedTask
from accounts.models import User
from winupdate.models import WinUpdatePolicy
from software.models import InstalledSoftware
from checks.serializers import CheckRunnerGetSerializer
from agents.serializers import WinAgentSerializer
from autotasks.serializers import TaskGOGetSerializer, TaskRunnerPatchSerializer
from winupdate.serializers import ApprovedUpdateSerializer

from agents.tasks import (
    agent_recovery_email_task,
    agent_recovery_sms_task,
)
from checks.utils import bytes2human
from tacticalrmm.utils import notify_error, reload_nats, filter_software, SoftwareList

logger.configure(**settings.LOG_CONFIG)


class CheckRunner(APIView):
    """
    For the windows golang agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        checks = Check.objects.filter(agent__pk=agent.pk, overriden_by_policy=False)

        ret = {
            "agent": agent.pk,
            "check_interval": agent.check_interval,
            "checks": CheckRunnerGetSerializer(checks, many=True).data,
        }
        return Response(ret)

    def patch(self, request):
        check = get_object_or_404(Check, pk=request.data["id"])
        check.last_run = djangotime.now()
        check.save(update_fields=["last_run"])
        status = check.handle_checkv2(request.data)

        return Response(status)


class CheckRunnerInterval(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        return Response({"agent": agent.pk, "check_interval": agent.check_interval})


class TaskRunner(APIView):
    """
    For the windows golang agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        task = get_object_or_404(AutomatedTask, pk=pk)
        return Response(TaskGOGetSerializer(task).data)

    def patch(self, request, pk, agentid):
        from logs.models import AuditLog

        agent = get_object_or_404(Agent, agent_id=agentid)
        task = get_object_or_404(AutomatedTask, pk=pk)

        serializer = TaskRunnerPatchSerializer(
            instance=task, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(last_run=djangotime.now())

        # create alert in dashboard if retcode is not 0
        if task.alert_severity and request.data["retcode"] > 0:
            from alerts.models import Alert

            Alert.create_task_alert(task, task.alert_severity)

            # TODO: send email/text alert if configured

        # resolve alert if passing
        elif task.alert_severity and request.data["retcode"] == 0:
            from alerts.models import Alert

            if Alert.objects.filter(task=task, resolved=False).exists():
                alert = Alert.objects.get(task=task, resolved=False)
                alert.resolve()

                # TODO: send resolved email/text alert if configured

        new_task = AutomatedTask.objects.get(pk=task.pk)
        AuditLog.objects.create(
            username=agent.hostname,
            agent=agent.hostname,
            object_type="agent",
            action="task_run",
            message=f"Scheduled Task {task.name} was run on {agent.hostname}",
            after_value=AutomatedTask.serialize(new_task),
        )

        return Response("ok")


class SysInfo(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

        if not isinstance(request.data["sysinfo"], dict):
            return notify_error("err")

        agent.wmi_detail = request.data["sysinfo"]
        agent.save(update_fields=["wmi_detail"])
        return Response("ok")


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


class NewAgent(APIView):
    def post(self, request):
        from logs.models import AuditLog

        """ Creates the agent """

        if Agent.objects.filter(agent_id=request.data["agent_id"]).exists():
            return notify_error(
                "Agent already exists. Remove old agent first if trying to re-install"
            )

        agent = Agent(
            agent_id=request.data["agent_id"],
            hostname=request.data["hostname"],
            site_id=int(request.data["site"]),
            monitoring_type=request.data["monitoring_type"],
            description=request.data["description"],
            mesh_node_id=request.data["mesh_node_id"],
            last_seen=djangotime.now(),
        )
        agent.save()
        agent.salt_id = f"{agent.hostname}-{agent.pk}"
        agent.save(update_fields=["salt_id"])

        user = User.objects.create_user(
            username=request.data["agent_id"],
            agent=agent,
            password=User.objects.make_random_password(60),
        )

        token = Token.objects.create(user=user)

        if agent.monitoring_type == "workstation":
            WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
        else:
            WinUpdatePolicy(agent=agent).save()

        reload_nats()

        # create agent install audit record
        AuditLog.objects.create(
            username=request.user,
            agent=agent.hostname,
            object_type="agent",
            action="agent_install",
            message=f"{request.user} installed new agent {agent.hostname}",
            after_value=Agent.serialize(agent),
        )

        return Response(
            {
                "pk": agent.pk,
                "saltid": f"{agent.hostname}-{agent.pk}",
                "token": token.key,
            }
        )


class Software(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        raw: SoftwareList = request.data["software"]
        if not isinstance(raw, list):
            return notify_error("err")

        sw = filter_software(raw)
        if not InstalledSoftware.objects.filter(agent=agent).exists():
            InstalledSoftware(agent=agent, software=sw).save()
        else:
            s = agent.installedsoftware_set.first()
            s.software = sw
            s.save(update_fields=["software"])

        return Response("ok")


class Installer(APIView):
    def get(self, request):
        # used to check if token is valid. will return 401 if not
        return Response("ok")

    def post(self, request):
        if "version" not in request.data:
            return notify_error("Invalid data")

        ver = request.data["version"]
        if pyver.parse(ver) < pyver.parse(settings.LATEST_AGENT_VER):
            return notify_error(
                f"Old installer detected (version {ver} ). Latest version is {settings.LATEST_AGENT_VER} Please generate a new installer from the RMM"
            )

        return Response("ok")
