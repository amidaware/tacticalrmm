from loguru import logger

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from agents.models import Agent
from checks.models import Check
from autotasks.models import AutomatedTask

from winupdate.tasks import check_for_updates_task

from autotasks.serializers import TaskRunnerGetSerializer, TaskRunnerPatchSerializer
from checks.serializers import CheckRunnerGetSerializer, CheckResultsSerializer


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
    For the windows python agent
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
        agent.save(update_fields=["salt_ver"])
        return Response("ok")
