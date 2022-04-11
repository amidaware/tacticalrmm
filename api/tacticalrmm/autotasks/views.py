from agents.models import Agent
from automation.models import Policy
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.permissions import _has_perm_on_agent

from .models import AutomatedTask
from .permissions import AutoTaskPerms, RunAutoTaskPerms
from .serializers import TaskSerializer


class GetAddAutoTasks(APIView):
    permission_classes = [IsAuthenticated, AutoTaskPerms]

    def get(self, request, agent_id=None, policy=None):

        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            tasks = agent.get_tasks_with_policies()
        elif policy:
            policy = get_object_or_404(Policy, id=policy)
            tasks = AutomatedTask.objects.filter(policy=policy)
        else:
            tasks = AutomatedTask.objects.filter_by_role(request.user)  # type: ignore
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        from autotasks.tasks import create_win_task_schedule

        data = request.data.copy()

        # Determine if adding to an agent and replace agent_id with pk
        if "agent" in data.keys():
            agent = get_object_or_404(Agent, agent_id=data["agent"])

            if not _has_perm_on_agent(request.user, agent.agent_id):
                raise PermissionDenied()

            data["agent"] = agent.pk

        serializer = TaskSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(
            win_task_name=AutomatedTask.generate_task_name(),
        )

        if task.agent:
            create_win_task_schedule.delay(pk=task.pk)

        return Response(
            "The task has been created. It will show up on the agent on next checkin"
        )


class GetEditDeleteAutoTask(APIView):
    permission_classes = [IsAuthenticated, AutoTaskPerms]

    def get(self, request, pk):

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        return Response(TaskSerializer(task).data)

    def put(self, request, pk):

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        serializer = TaskSerializer(instance=task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("The task was updated")

    def delete(self, request, pk):
        from autotasks.tasks import delete_win_task_schedule

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        if task.agent:
            delete_win_task_schedule.delay(pk=task.pk)
        else:
            task.delete()

        return Response(f"{task.name} will be deleted shortly")


class RunAutoTask(APIView):
    permission_classes = [IsAuthenticated, RunAutoTaskPerms]

    def post(self, request, pk):
        from autotasks.tasks import run_win_task

        task = get_object_or_404(AutomatedTask, pk=pk)

        if task.agent and not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()

        # run policy task on agent
        if "agent_id" in request.data.keys():
            if not _has_perm_on_agent(request.user, request.data["agent_id"]):
                raise PermissionDenied()

            run_win_task.delay(pk=pk, agent_id=request.data["agent_id"])

        # run normal task on agent
        else:
            run_win_task.delay(pk=pk)
        return Response(f"{task.name} will now be run.")
