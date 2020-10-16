from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from agents.models import Agent
from checks.models import Check
from autotasks.models import AutomatedTask
from winupdate.models import WinUpdate
from checks.serializers import (
    CheckResultsSerializer,
    CheckRunnerGetSerializerV3,
)
from agents.serializers import WinAgentSerializer
from autotasks.serializers import TaskGOGetSerializer, TaskRunnerPatchSerializer
from winupdate.serializers import ApprovedUpdateSerializer

from agents.tasks import (
    agent_recovery_email_task,
    get_wmi_detail_task,
    sync_salt_modules_task,
)
from winupdate.tasks import check_for_updates_task
from software.tasks import get_installed_software, install_chocolatey
from checks.utils import bytes2human


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

        serializer.save(last_seen=djangotime.now(), disks=new)

        if agent.agentoutages.exists() and agent.agentoutages.last().is_active:
            last_outage = agent.agentoutages.last()
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


class WinUpdater(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        agent.delete_superseded_updates()
        patches = WinUpdate.objects.filter(agent=agent, action="approve").exclude(
            installed=True
        )
        return Response(ApprovedUpdateSerializer(patches, many=True).data)


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