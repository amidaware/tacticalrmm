from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from checks.models import Check
from scripts.models import Script
from tacticalrmm.utils import get_bit_days, get_default_timezone, notify_error

from .models import AutomatedTask
from .permissions import ManageAutoTaskPerms, RunAutoTaskPerms
from .serializers import AutoTaskSerializer, TaskSerializer


class AddAutoTask(APIView):
    permission_classes = [IsAuthenticated, ManageAutoTaskPerms]

    def post(self, request):
        from automation.models import Policy
        from automation.tasks import generate_agent_autotasks_task
        from autotasks.tasks import create_win_task_schedule

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

        bit_weekdays = None
        if data["autotask"]["run_time_days"]:
            bit_weekdays = get_bit_days(data["autotask"]["run_time_days"])

        del data["autotask"]["run_time_days"]
        serializer = TaskSerializer(data=data["autotask"], partial=True, context=parent)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(
            **parent,
            script=script,
            win_task_name=AutomatedTask.generate_task_name(),
            assigned_check=check,
            run_time_bit_weekdays=bit_weekdays,
        )

        if task.agent:
            create_win_task_schedule.delay(pk=task.pk)

        elif task.policy:
            generate_agent_autotasks_task.delay(policy=task.policy.pk)

        return Response("Task will be created shortly!")


class AutoTask(APIView):
    permission_classes = [IsAuthenticated, ManageAutoTaskPerms]

    def get(self, request, pk):

        agent = get_object_or_404(Agent, pk=pk)
        ctx = {
            "default_tz": get_default_timezone(),
            "agent_tz": agent.time_zone,
        }
        return Response(AutoTaskSerializer(agent, context=ctx).data)

    def put(self, request, pk):
        from automation.tasks import update_policy_autotasks_fields_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        serializer = TaskSerializer(instance=task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if task.policy:
            update_policy_autotasks_fields_task.delay(task=task.pk)

        return Response("ok")

    def patch(self, request, pk):
        from automation.tasks import update_policy_autotasks_fields_task
        from autotasks.tasks import enable_or_disable_win_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if "enableordisable" in request.data:
            action = request.data["enableordisable"]
            task.enabled = action
            task.save(update_fields=["enabled"])
            action = "enabled" if action else "disabled"

            if task.policy:
                update_policy_autotasks_fields_task.delay(
                    task=task.pk, update_agent=True
                )
            elif task.agent:
                enable_or_disable_win_task.delay(pk=task.pk)

            return Response(f"Task will be {action} shortly")

        else:
            return notify_error("The request was invalid")

    def delete(self, request, pk):
        from automation.tasks import delete_policy_autotasks_task
        from autotasks.tasks import delete_win_task_schedule

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent:
            delete_win_task_schedule.delay(pk=task.pk)
        elif task.policy:
            delete_policy_autotasks_task.delay(task=task.pk)
            task.delete()

        return Response(f"{task.name} will be deleted shortly")


@api_view()
@permission_classes([IsAuthenticated, RunAutoTaskPerms])
def run_task(request, pk):
    from autotasks.tasks import run_win_task

    task = get_object_or_404(AutomatedTask, pk=pk)
    run_win_task.delay(pk=pk)
    return Response(f"{task.name} will now be run on {task.agent.hostname}")
