import asyncio
import os
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from packaging import version as pyver
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from agents.models import Agent, AgentHistory
from agents.serializers import AgentHistorySerializer
from autotasks.models import AutomatedTask
from autotasks.serializers import TaskGOGetSerializer, TaskRunnerPatchSerializer
from checks.models import Check
from checks.serializers import CheckRunnerGetSerializer
from logs.models import PendingAction, DebugLog
from software.models import InstalledSoftware
from tacticalrmm.utils import notify_error, reload_nats
from winupdate.models import WinUpdate, WinUpdatePolicy


class CheckIn(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # called once during tacticalagent windows service startup
    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if not agent.choco_installed:
            asyncio.run(agent.nats_cmd({"func": "installchoco"}, wait=False))

        time.sleep(0.5)
        asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
        return Response("ok")


class SyncMeshNodeID(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if agent.mesh_node_id != request.data["nodeid"]:
            agent.mesh_node_id = request.data["nodeid"]
            agent.save(update_fields=["mesh_node_id"])

        return Response("ok")


class Choco(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        agent.choco_installed = request.data["installed"]
        agent.save(update_fields=["choco_installed"])
        return Response("ok")


class WinUpdates(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])

        needs_reboot: bool = request.data["needs_reboot"]
        agent.needs_reboot = needs_reboot
        agent.save(update_fields=["needs_reboot"])

        reboot_policy: str = agent.get_patch_policy().reboot_after_install
        reboot = False

        if reboot_policy == "always":
            reboot = True
        elif needs_reboot and reboot_policy == "required":
            reboot = True

        if reboot:
            asyncio.run(agent.nats_cmd({"func": "rebootnow"}, wait=False))
            DebugLog.info(
                agent=agent,
                log_type="windows_updates",
                message=f"{agent.hostname} is rebooting after updates were installed.",
            )

        agent.delete_superseded_updates()
        return Response("ok")

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        u = agent.winupdates.filter(guid=request.data["guid"]).last()  # type: ignore
        success: bool = request.data["success"]
        if success:
            u.result = "success"
            u.downloaded = True
            u.installed = True
            u.date_installed = djangotime.now()
            u.save(
                update_fields=[
                    "result",
                    "downloaded",
                    "installed",
                    "date_installed",
                ]
            )
        else:
            u.result = "failed"
            u.save(update_fields=["result"])

        agent.delete_superseded_updates()
        return Response("ok")

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        updates = request.data["wua_updates"]
        for update in updates:
            if agent.winupdates.filter(guid=update["guid"]).exists():  # type: ignore
                u = agent.winupdates.filter(guid=update["guid"]).last()  # type: ignore
                u.downloaded = update["downloaded"]
                u.installed = update["installed"]
                u.save(update_fields=["downloaded", "installed"])
            else:
                try:
                    kb = "KB" + update["kb_article_ids"][0]
                except:
                    continue

                WinUpdate(
                    agent=agent,
                    guid=update["guid"],
                    kb=kb,
                    title=update["title"],
                    installed=update["installed"],
                    downloaded=update["downloaded"],
                    description=update["description"],
                    severity=update["severity"],
                    categories=update["categories"],
                    category_ids=update["category_ids"],
                    kb_article_ids=update["kb_article_ids"],
                    more_info_urls=update["more_info_urls"],
                    support_url=update["support_url"],
                    revision_number=update["revision_number"],
                ).save()

        agent.delete_superseded_updates()
        return Response("ok")


class SupersededWinUpdate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        updates = agent.winupdates.filter(guid=request.data["guid"])  # type: ignore
        for u in updates:
            u.delete()

        return Response("ok")


class RunChecks(APIView):
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


class CheckRunner(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        checks = agent.agentchecks.filter(overriden_by_policy=False)  # type: ignore

        run_list = [
            check
            for check in checks
            # always run if check hasn't run yet
            if not check.last_run
            # if a check interval is set, see if the correct amount of seconds have passed
            or (
                check.run_interval
                and (
                    check.last_run
                    < djangotime.now()
                    - djangotime.timedelta(seconds=check.run_interval)
                )
            )
            # if check interval isn't set, make sure the agent's check interval has passed before running
            or (
                not check.run_interval
                and check.last_run
                < djangotime.now() - djangotime.timedelta(seconds=agent.check_interval)
            )
        ]
        ret = {
            "agent": agent.pk,
            "check_interval": agent.check_run_interval(),
            "checks": CheckRunnerGetSerializer(run_list, many=True).data,
        }
        return Response(ret)

    def patch(self, request):
        check = get_object_or_404(Check, pk=request.data["id"])

        check.last_run = djangotime.now()
        check.save(update_fields=["last_run"])
        status = check.handle_check(request.data)
        if status == "failing" and check.assignedtask.exists():  # type: ignore
            check.handle_assigned_task()

        return Response("ok")


class CheckRunnerInterval(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)

        return Response(
            {"agent": agent.pk, "check_interval": agent.check_run_interval()}
        )


class TaskRunner(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, agentid):
        _ = get_object_or_404(Agent, agent_id=agentid)
        task = get_object_or_404(AutomatedTask, pk=pk)
        return Response(TaskGOGetSerializer(task).data)

    def patch(self, request, pk, agentid):
        from alerts.models import Alert

        agent = get_object_or_404(Agent, agent_id=agentid)
        task = get_object_or_404(AutomatedTask, pk=pk)

        serializer = TaskRunnerPatchSerializer(
            instance=task, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        new_task = serializer.save(last_run=djangotime.now())

        AgentHistory.objects.create(
            agent=agent,
            type="task_run",
            script=task.script,
            script_results=request.data,
        )

        # check if task is a collector and update the custom field
        if task.custom_field:
            if not task.stderr:

                task.save_collector_results()

                status = "passing"
            else:
                status = "failing"
        else:
            status = "failing" if task.retcode != 0 else "passing"

        new_task.status = status
        new_task.save()

        if status == "passing":
            if Alert.objects.filter(assigned_task=new_task, resolved=False).exists():
                Alert.handle_alert_resolve(new_task)
        else:
            Alert.handle_alert_failure(new_task)

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
    """Sends the mesh exe to the installer"""

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

        user = User.objects.create_user(  # type: ignore
            username=request.data["agent_id"],
            agent=agent,
            password=User.objects.make_random_password(60),  # type: ignore
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
            debug_info={"ip": request._client_ip},
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
        sw = request.data["software"]
        if not InstalledSoftware.objects.filter(agent=agent).exists():
            InstalledSoftware(agent=agent, software=sw).save()
        else:
            s = agent.installedsoftware_set.first()  # type: ignore
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


class ChocoResult(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        action = get_object_or_404(PendingAction, pk=pk)
        results: str = request.data["results"]

        software_name = action.details["name"].lower()
        success = [
            "install",
            "of",
            software_name,
            "was",
            "successful",
            "installed",
        ]
        duplicate = [software_name, "already", "installed", "--force", "reinstall"]
        installed = False

        if all(x in results.lower() for x in success):
            installed = True
        elif all(x in results.lower() for x in duplicate):
            installed = True

        action.details["output"] = results
        action.details["installed"] = installed
        action.status = "completed"
        action.save(update_fields=["details", "status"])
        return Response("ok")


class AgentRecovery(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(
            Agent.objects.prefetch_related("recoveryactions").only(
                "pk", "agent_id", "last_seen"
            ),
            agent_id=agentid,
        )

        # TODO remove these 2 lines after agent v1.7.0 has been out for a while
        # this is handled now by nats-api service
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["last_seen"])

        recovery = agent.recoveryactions.filter(last_run=None).last()  # type: ignore
        ret = {"mode": "pass", "shellcmd": ""}
        if recovery is None:
            return Response(ret)

        recovery.last_run = djangotime.now()
        recovery.save(update_fields=["last_run"])

        ret["mode"] = recovery.mode

        if recovery.mode == "command":
            ret["shellcmd"] = recovery.command
        elif recovery.mode == "rpc":
            reload_nats()

        return Response(ret)


class AgentHistoryResult(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, agentid, pk):
        _ = get_object_or_404(Agent, agent_id=agentid)
        hist = get_object_or_404(AgentHistory, pk=pk)
        s = AgentHistorySerializer(instance=hist, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response("ok")
