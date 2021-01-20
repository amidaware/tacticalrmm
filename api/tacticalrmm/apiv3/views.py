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
from checks.serializers import CheckRunnerGetSerializerV3
from agents.serializers import WinAgentSerializer
from autotasks.serializers import TaskGOGetSerializer, TaskRunnerPatchSerializer
from winupdate.serializers import ApprovedUpdateSerializer

from agents.tasks import (
    agent_recovery_email_task,
    agent_recovery_sms_task,
    install_salt_task,
)
from checks.utils import bytes2human
from tacticalrmm.utils import notify_error, reload_nats, filter_software, SoftwareList

logger.configure(**settings.LOG_CONFIG)


class CheckIn(APIView):
    """
    The agent's checkin endpoint
    patch: called every 45 to 110 seconds, handles agent updates and recovery
    put: called every 5 to 10 minutes, handles basic system info
    post: called once on windows service startup
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        agent.version = request.data["version"]
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["version", "last_seen"])

        if agent.agentoutages.exists() and agent.agentoutages.last().is_active:
            last_outage = agent.agentoutages.last()
            last_outage.recovery_time = djangotime.now()
            last_outage.save(update_fields=["recovery_time"])

            if agent.overdue_email_alert:
                agent_recovery_email_task.delay(pk=last_outage.pk)
            if agent.overdue_text_alert:
                agent_recovery_sms_task.delay(pk=last_outage.pk)

        recovery = agent.recoveryactions.filter(last_run=None).last()
        if recovery is not None:
            recovery.last_run = djangotime.now()
            recovery.save(update_fields=["last_run"])
            return Response(recovery.send())

        # handle agent update
        if agent.pendingactions.filter(
            action_type="agentupdate", status="pending"
        ).exists():
            update = agent.pendingactions.filter(
                action_type="agentupdate", status="pending"
            ).last()
            update.status = "completed"
            update.save(update_fields=["status"])
            return Response(update.details)

        # get any pending actions
        if agent.pendingactions.filter(status="pending").exists():
            agent.handle_pending_actions()

        return Response("ok")

    def put(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "disks" in request.data.keys():
            disks = request.data["disks"]
            new = []
            # python agent
            if isinstance(disks, dict):
                for k, v in disks.items():
                    new.append(v)
            else:
                # golang agent
                for disk in disks:
                    tmp = {}
                    for k, v in disk.items():
                        tmp["device"] = disk["device"]
                        tmp["fstype"] = disk["fstype"]
                        tmp["total"] = bytes2human(disk["total"])
                        tmp["used"] = bytes2human(disk["used"])
                        tmp["free"] = bytes2human(disk["free"])
                        tmp["percent"] = int(disk["percent"])
                    new.append(tmp)

            serializer.save(disks=new)
            return Response("ok")

        if "logged_in_username" in request.data.keys():
            if request.data["logged_in_username"] != "None":
                serializer.save(last_logged_in_user=request.data["logged_in_username"])
                return Response("ok")

        serializer.save()
        return Response("ok")

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

        serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_seen=djangotime.now())
        return Response("ok")


class Hello(APIView):
    #### DEPRECATED, for agents <= 1.1.9 ####
    """
    The agent's checkin endpoint
    patch: called every 30 to 120 seconds
    post: called on agent windows service startup
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        disks = request.data["disks"]
        new = []
        # python agent
        if isinstance(disks, dict):
            for k, v in disks.items():
                new.append(v)
        else:
            # golang agent
            for disk in disks:
                tmp = {}
                for k, v in disk.items():
                    tmp["device"] = disk["device"]
                    tmp["fstype"] = disk["fstype"]
                    tmp["total"] = bytes2human(disk["total"])
                    tmp["used"] = bytes2human(disk["used"])
                    tmp["free"] = bytes2human(disk["free"])
                    tmp["percent"] = int(disk["percent"])
                new.append(tmp)

        if request.data["logged_in_username"] == "None":
            serializer.save(last_seen=djangotime.now(), disks=new)
        else:
            serializer.save(
                last_seen=djangotime.now(),
                disks=new,
                last_logged_in_user=request.data["logged_in_username"],
            )

        if agent.agentoutages.exists() and agent.agentoutages.last().is_active:
            last_outage = agent.agentoutages.last()
            last_outage.recovery_time = djangotime.now()
            last_outage.save(update_fields=["recovery_time"])

            if agent.overdue_email_alert:
                agent_recovery_email_task.delay(pk=last_outage.pk)
            if agent.overdue_text_alert:
                agent_recovery_sms_task.delay(pk=last_outage.pk)

        recovery = agent.recoveryactions.filter(last_run=None).last()
        if recovery is not None:
            recovery.last_run = djangotime.now()
            recovery.save(update_fields=["last_run"])
            return Response(recovery.send())

        # handle agent update
        if agent.pendingactions.filter(
            action_type="agentupdate", status="pending"
        ).exists():
            update = agent.pendingactions.filter(
                action_type="agentupdate", status="pending"
            ).last()
            update.status = "completed"
            update.save(update_fields=["status"])
            return Response(update.details)

        # get any pending actions
        if agent.pendingactions.filter(status="pending").exists():
            agent.handle_pending_actions()

        return Response("ok")

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

        serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_seen=djangotime.now())
        return Response("ok")


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
            "checks": CheckRunnerGetSerializerV3(checks, many=True).data,
        }
        return Response(ret)

    def patch(self, request):
        check = get_object_or_404(Check, pk=request.data["id"])
        check.last_run = djangotime.now()
        check.save(update_fields=["last_run"])
        status = check.handle_checkv2(request.data)

        return Response(status)


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


class WinUpdater(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        agent.delete_superseded_updates()
        patches = agent.winupdates.filter(action="approve").exclude(installed=True)
        return Response(ApprovedUpdateSerializer(patches, many=True).data)

    # agent sends patch results as it's installing them
    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        kb = request.data["kb"]
        results = request.data["results"]
        update = agent.winupdates.get(kb=kb)

        if results == "error" or results == "failed":
            update.result = results
            update.save(update_fields=["result"])
        elif results == "success":
            update.result = "success"
            update.downloaded = True
            update.installed = True
            update.date_installed = djangotime.now()
            update.save(
                update_fields=[
                    "result",
                    "downloaded",
                    "installed",
                    "date_installed",
                ]
            )
        elif results == "alreadyinstalled":
            update.result = "success"
            update.downloaded = True
            update.installed = True
            update.save(update_fields=["result", "downloaded", "installed"])

        return Response("ok")

    # agent calls this after it's finished installing all patches
    def post(self, request):
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
            if agent.has_nats:
                asyncio.run(agent.nats_cmd({"func": "rebootnow"}, wait=False))
                logger.info(
                    f"{agent.hostname} is rebooting after updates were installed."
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


class MeshInfo(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        return Response(agent.mesh_node_id)

    def patch(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)

        if "nodeidhex" in request.data:
            # agent <= 1.1.0
            nodeid = request.data["nodeidhex"]
        else:
            # agent >= 1.1.1
            nodeid = request.data["nodeid"]

        agent.mesh_node_id = nodeid
        agent.save(update_fields=["mesh_node_id"])
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

        # Generate policies for new agent
        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

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


class InstallSalt(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        install_salt_task.delay(agent.pk)
        return Response("ok")
