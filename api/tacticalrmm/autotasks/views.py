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
from checks.models import Script
from automation.models import Policy

from .serializers import AutoTaskSerializer, AgentTaskSerializer
from checks.serializers import ScriptSerializer

from .tasks import (
    create_win_task_schedule,
    delete_win_task_schedule,
    run_win_task,
    enable_or_disable_win_task,
)

class AddAutoTask(APIView):
    def post(self, request):
        daily, checkfailure, manual = False, False, False
        data = request.data

        # Determine if adding check to Policy or Agent
        if "policy" in data:
            policy = get_object_or_404(Policy, id=data["policy"])

            # Object used for filter and save
            parent = {"policy": policy}
        else:
            agent = get_object_or_404(Agent, pk=data["agent"])
            # Object used for filter and save
            parent = {"agent": agent}

        script = Script.objects.only("pk").get(pk=data["script"])
        if data["trigger"] == "daily":
            daily = True
            days = data["days"]
            time = data["time"]
        elif data["trigger"] == "checkfailure":
            checkfailure = True
            check = data["check"]
        elif data["trigger"] == "manual":
            manual = True

        rand_name = AutomatedTask.generate_task_name()

        try:
            timeout = data["timeout"]
        except KeyError:
            timeout = 130

        if daily:
            task = AutomatedTask(
                **parent,
                name=data["name"],
                script=script,
                timeout=timeout,
                task_type="scheduled",
                win_task_name=rand_name,
                run_time_days=data["days"],
                run_time_minute=data["time"],
            )
            task.save()

        elif checkfailure:
            task = AutomatedTask(
                **parent,
                name=data["name"],
                script=script,
                timeout=timeout,
                win_task_name=rand_name,
                task_type="checkfailure",
            )
            task.save()
            related_check = AutomatedTask.get_related_check(check)
            related_check.task_on_failure = task
            related_check.save(update_fields=["task_on_failure"])

        elif manual:
            task = AutomatedTask(
                **parent,
                name=data["name"],
                timeout=timeout,
                win_task_name=rand_name,
                script=script,
                task_type="manual",
            )
            task.save()

        create_win_task_schedule.delay(pk=task.pk)
        return Response("ok")

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
