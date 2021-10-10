from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from agents.models import Agent
from automation.models import Policy
from tacticalrmm.utils import get_bit_days
from tacticalrmm.permissions import _has_perm_on_agent

from .models import AutomatedTask
from .permissions import AutoTaskPerms, RunAutoTaskPerms
from .serializers import TaskSerializer


class GetAddAutoTasks(APIView):
    permission_classes = [IsAuthenticated, AutoTaskPerms]

    def get(self, request, agent_id=None, policy=None):
        
        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            tasks = AutomatedTask.objects.filter(agent=agent)
        elif policy:
            policy = get_object_or_404(Policy, id=policy)
            tasks = AutomatedTask.objects.filter(policy=policy)
        else:
            tasks = AutomatedTask.permissions.filter_by_role(request.user)
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        from automation.tasks import generate_agent_autotasks_task
        from autotasks.tasks import create_win_task_schedule

        data = request.data.copy()

        # Determine if adding to an agent and replace agent_id with pk
        if "agent" in data.keys():
            agent = get_object_or_404(Agent, pk=data["agent"])

            if _has_perm_on_agent(request.user, agent.agent_id):
                raise PermissionDenied()

            data["agent"] = agent.pk

        bit_weekdays = None
        if "run_time_days" in data.keys():
            if data["run_time_days"]:
                bit_weekdays = get_bit_days(data["run_time_days"])
            data.pop("run_time_days")

        serializer = TaskSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(
            win_task_name=AutomatedTask.generate_task_name(),
            run_time_bit_weekdays=bit_weekdays,
        )

        if task.agent:
            create_win_task_schedule.delay(pk=task.pk)

        elif task.policy:
            generate_agent_autotasks_task.delay(policy=task.policy.pk)

        return Response("The task has been created. It will show up on the agent on next checkin")


class GetEditDeleteAutoTask(APIView):
    permission_classes = [IsAuthenticated, AutoTaskPerms]

    def get(self, request, pk):

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        return Response(TaskSerializer(task).data)

    def put(self, request, pk):
        from automation.tasks import update_policy_autotasks_fields_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        serializer = TaskSerializer(instance=task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if task.policy:
            update_policy_autotasks_fields_task.delay(task=task.pk)

        return Response("The task was updated")

    def delete(self, request, pk):
        from automation.tasks import delete_policy_autotasks_task
        from autotasks.tasks import delete_win_task_schedule

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        if task.agent:
            delete_win_task_schedule.delay(pk=task.pk)
        elif task.policy:
            delete_policy_autotasks_task.delay(task=task.pk)
            task.delete()

        return Response(f"{task.name} will be deleted shortly")

class RunAutoTask(APIView):
    permission_classes = [IsAuthenticated, RunAutoTaskPerms]

    def post(self, request, pk):
        from autotasks.tasks import run_win_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        run_win_task.delay(pk=pk)
        return Response(f"{task.name} will now be run on {task.agent.hostname}")
