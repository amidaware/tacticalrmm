import os
import requests
from loguru import logger

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
from winupdate.models import WinUpdate
from accounts.models import User
from clients.models import Client, Site
from winupdate.models import WinUpdatePolicy
from checks.serializers import CheckRunnerGetSerializerV3
from agents.serializers import WinAgentSerializer
from autotasks.serializers import TaskGOGetSerializer, TaskRunnerPatchSerializer
from winupdate.serializers import ApprovedUpdateSerializer

from agents.tasks import (
    agent_recovery_email_task,
    agent_recovery_sms_task,
    get_wmi_detail_task,
    sync_salt_modules_task,
)
from winupdate.tasks import check_for_updates_task
from software.tasks import get_installed_software, install_chocolatey
from checks.utils import bytes2human
from tacticalrmm.utils import notify_error

logger.configure(**settings.LOG_CONFIG)


class Hello(APIView):
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

        # get any pending actions
        if agent.pendingactions.filter(status="pending").exists():
            agent.handle_pending_actions()

        return Response("ok")

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

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


class CheckRunner(APIView):
    """
    For the windows golang agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["last_seen"])
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
        agent = get_object_or_404(Agent, agent_id=agentid)
        task = get_object_or_404(AutomatedTask, pk=pk)

        serializer = TaskRunnerPatchSerializer(
            instance=task, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(last_run=djangotime.now())
        return Response("ok")


class SaltMinion(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        ret = {
            "latestVer": settings.LATEST_SALT_VER,
            "currentVer": agent.salt_ver,
            "salt_id": agent.salt_id,
            "downloadURL": agent.winsalt_dl,
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
        r = agent.salt_api_cmd(timeout=45, func="saltutil.sync_modules")

        if r == "timeout" or r == "error":
            return notify_error("Failed to sync salt modules")

        if isinstance(r, list) and any("modules" in i for i in r):
            return Response("Successfully synced salt modules")
        elif isinstance(r, list) and not r:
            return Response("Modules are already in sync")
        else:
            return notify_error(f"Failed to sync salt modules: {str(r)}")

    def put(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        agent.salt_ver = request.data["ver"]
        agent.save(update_fields=["salt_ver"])
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
                logger.info(
                    f"{agent.hostname} is rebooting after updates were installed."
                )
        else:
            check_for_updates_task.apply_async(
                queue="wupdate", kwargs={"pk": agent.pk, "wait": False}
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
        agent.mesh_node_id = request.data["nodeidhex"]
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