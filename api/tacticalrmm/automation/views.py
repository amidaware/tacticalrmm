from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Policy
from agents.models import Agent
from clients.models import Client
from checks.models import Check
from autotasks.models import AutomatedTask
from winupdate.models import WinUpdatePolicy

from winupdate.serializers import WinUpdatePolicySerializer

from .serializers import (
    PolicySerializer,
    PolicyTableSerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
    PolicyCheckSerializer,
    PolicyTaskStatusSerializer,
    AutoTasksFieldSerializer,
)

from .tasks import (
    run_win_policy_autotask_task,
)


class GetAddPolicies(APIView):
    def get(self, request):
        policies = Policy.objects.all()

        return Response(PolicyTableSerializer(policies, many=True).data)

    def post(self, request):
        serializer = PolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()

        # copy checks and tasks from specified policy
        if "copyId" in request.data:
            copyPolicy = Policy.objects.get(pk=request.data["copyId"])

            checks = copyPolicy.policychecks.all()
            for check in checks:
                check.create_policy_check(policy=policy)

            tasks = copyPolicy.autotasks.all()

            for task in tasks:
                task.create_policy_task(policy=policy)

        return Response("ok")


class GetUpdateDeletePolicy(APIView):
    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicySerializer(policy).data)

    def put(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        serializer = PolicySerializer(instance=policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(Policy, pk=pk).delete()

        return Response("ok")


class PolicyAutoTask(APIView):

    # tasks associated with policy
    def get(self, request, pk):
        tasks = AutomatedTask.objects.filter(policy=pk)
        return Response(AutoTasksFieldSerializer(tasks, many=True).data)

    # get status of all tasks
    def patch(self, request, task):
        tasks = AutomatedTask.objects.filter(parent_task=task)
        return Response(PolicyTaskStatusSerializer(tasks, many=True).data)

    # bulk run win tasks associated with policy
    def put(self, request, task):
        tasks = AutomatedTask.objects.filter(parent_task=task)
        run_win_policy_autotask_task.delay([task.id for task in tasks])
        return Response("Affected agent tasks will run shortly")


class PolicyCheck(APIView):
    def get(self, request, pk):
        checks = Check.objects.filter(policy__pk=pk, agent=None)
        return Response(PolicyCheckSerializer(checks, many=True).data)

    def patch(self, request, check):
        checks = Check.objects.filter(parent_check=check)
        return Response(PolicyCheckStatusSerializer(checks, many=True).data)


class OverviewPolicy(APIView):
    def get(self, request):

        clients = Client.objects.all()
        return Response(PolicyOverviewSerializer(clients, many=True).data)


class UpdatePatchPolicy(APIView):

    # create new patch policy
    def post(self, request):
        policy = get_object_or_404(Policy, pk=request.data["policy"])

        serializer = WinUpdatePolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.policy = policy
        serializer.save()

        return Response("ok")

    # update patch policy
    def put(self, request, patchpolicy):
        policy = get_object_or_404(WinUpdatePolicy, pk=patchpolicy)

        serializer = WinUpdatePolicySerializer(
            instance=policy, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    # bulk reset agent patch policy
    def patch(self, request):

        agents = None
        if "client" in request.data:
            agents = Agent.objects.prefetch_related("winupdatepolicy").filter(
                site__client_id=request.data["client"]
            )
        elif "site" in request.data:
            agents = Agent.objects.prefetch_related("winupdatepolicy").filter(
                site_id=request.data["site"]
            )
        else:
            agents = Agent.objects.prefetch_related("winupdatepolicy").only("pk")

        for agent in agents:
            winupdatepolicy = agent.winupdatepolicy.get()
            winupdatepolicy.critical = "inherit"
            winupdatepolicy.important = "inherit"
            winupdatepolicy.moderate = "inherit"
            winupdatepolicy.low = "inherit"
            winupdatepolicy.other = "inherit"
            winupdatepolicy.run_time_frequency = "inherit"
            winupdatepolicy.reboot_after_install = "inherit"
            winupdatepolicy.reprocess_failed_inherit = True
            winupdatepolicy.save(
                update_fields=[
                    "critical",
                    "important",
                    "moderate",
                    "low",
                    "other",
                    "run_time_frequency",
                    "reboot_after_install",
                    "reprocess_failed_inherit",
                ]
            )

        return Response("ok")

    # delete patch policy
    def delete(self, request, patchpolicy):
        get_object_or_404(WinUpdatePolicy, pk=patchpolicy).delete()

        return Response("ok")
