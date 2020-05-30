import datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view

from .models import AutomatedTask
from agents.models import Agent
from checks.models import Check

from scripts.models import Script
from automation.models import Policy

from .serializers import TaskSerializer, AutoTaskSerializer, AgentTaskSerializer
from scripts.serializers import ScriptSerializer

from .tasks import (
    create_win_task_schedule,
    delete_win_task_schedule,
    run_win_task,
    enable_or_disable_win_task,
)


class AddAutoTask(APIView):
    def post(self, request):

        data = request.data
        script = get_object_or_404(Script, pk=data["autotask"]["script"])

        # Determine if adding check to Policy or Agent
        if "policy" in data:
            policy = get_object_or_404(Policy, id=data["policy"])
            # Object used for filter and save
            parent = {"policy": policy}
        else:
            agent = get_object_or_404(Agent, pk=data["agent"])
            parent = {"agent": agent}

        check = None
        if data["autotask"]["assigned_check"]:
            check = get_object_or_404(Check, pk=data["autotask"]["assigned_check"])

        serializer = TaskSerializer(data=data["autotask"], partial=True, context=parent)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(
            **parent,
            script=script,
            win_task_name=AutomatedTask.generate_task_name(),
            assigned_check=check,
        )

        create_win_task_schedule.delay(pk=obj.pk)

        return Response("Task will be created shortly!")


class AutoTask(APIView):
    def get(self, request, pk):

        agent = Agent.objects.only("pk").get(pk=pk)
        return Response(AutoTaskSerializer(agent).data)

    def patch(self, request, pk):
        task = get_object_or_404(AutomatedTask, pk=pk)

        if "enableordisable" in request.data:
            action = request.data["enableordisable"]
            enable_or_disable_win_task.delay(pk=task.pk, action=action)
            task.enabled = action
            task.save(update_fields=["enabled"])
            action = "enabled" if action else "disabled"
            return Response(f"Task will be {action} shortly")

    def delete(self, request, pk):
        task = get_object_or_404(AutomatedTask, pk=pk)
        delete_win_task_schedule.delay(pk=task.pk)
        return Response(f"{task.name} will be deleted shortly")


@api_view()
def run_task(request, pk):
    task = get_object_or_404(AutomatedTask, pk=pk)
    run_win_task.delay(task.pk)
    return Response(f"{task.name} will now be run on {task.agent.hostname}")


class TaskRunner(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        task = get_object_or_404(AutomatedTask, pk=pk)
        return Response(AgentTaskSerializer(task).data)

    def patch(self, request, pk):
        task = get_object_or_404(AutomatedTask, pk=pk)
        task.stdout = request.data["stdout"]
        task.stderr = request.data["stderr"]
        task.retcode = request.data["retcode"]
        task.execution_time = request.data["execution_time"]
        task.last_run = dt.datetime.now(tz=djangotime.utc)
        task.save(
            update_fields=["stdout", "stderr", "retcode", "last_run", "execution_time"]
        )
        return Response("ok")
