import pytz
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from .models import AutomatedTask
from agents.models import Agent
from checks.models import Check

from scripts.models import Script
from core.models import CoreSettings

from .serializers import TaskSerializer, AutoTaskSerializer

from .tasks import (
    create_win_task_schedule,
    delete_win_task_schedule,
    run_win_task,
    enable_or_disable_win_task,
)
from tacticalrmm.utils import notify_error


class AddAutoTask(APIView):
    def post(self, request):
        from automation.tasks import generate_agent_tasks_from_policies_task
        from automation.models import Policy

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
            added = "0.11.0"
            if data["autotask"]["script_args"] and agent.not_supported(added):
                return notify_error(
                    f"Script arguments only available in agent {added} or greater"
                )

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

        if not "policy" in data:
            create_win_task_schedule.delay(pk=obj.pk)

        if "policy" in data:
            generate_agent_tasks_from_policies_task.delay(data["policy"])

        return Response("Task will be created shortly!")


class AutoTask(APIView):
    def get(self, request, pk):

        agent = get_object_or_404(Agent, pk=pk)
        ctx = {
            "default_tz": pytz.timezone(CoreSettings.objects.first().default_time_zone),
            "agent_tz": agent.time_zone,
        }
        return Response(AutoTaskSerializer(agent, context=ctx).data)

    def patch(self, request, pk):
        from automation.tasks import update_policy_task_fields_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if "enableordisable" in request.data:
            action = request.data["enableordisable"]

            if not task.policy:
                enable_or_disable_win_task.delay(pk=task.pk, action=action)

            else:
                update_policy_task_fields_task.delay(task.pk, action)

            task.enabled = action
            task.save(update_fields=["enabled"])
            action = "enabled" if action else "disabled"
            return Response(f"Task will be {action} shortly")

    def delete(self, request, pk):
        from automation.tasks import delete_policy_autotask_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if not task.policy:
            delete_win_task_schedule.delay(pk=task.pk)

        if task.policy:
            delete_policy_autotask_task.delay(task.pk)
            task.delete()

        return Response(f"{task.name} will be deleted shortly")


@api_view()
def run_task(request, pk):
    task = get_object_or_404(AutomatedTask, pk=pk)
    run_win_task.delay(task.pk)
    return Response(f"{task.name} will now be run on {task.agent.hostname}")
