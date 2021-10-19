from agents.models import Agent
from agents.serializers import AgentHostnameSerializer
from autotasks.models import AutomatedTask
from checks.models import Check
from clients.models import Client
from clients.serializers import ClientSerializer, SiteSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tacticalrmm.utils import notify_error
from winupdate.models import WinUpdatePolicy
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Policy
from .permissions import AutomationPolicyPerms
from .serializers import (
    AutoTasksFieldSerializer,
    PolicyCheckStatusSerializer,
    PolicyRelatedSerializer,
    PolicyOverviewSerializer,
    PolicySerializer,
    PolicyTableSerializer,
    PolicyTaskStatusSerializer,
)


class GetAddPolicies(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

    def get(self, request):
        policies = Policy.objects.all()

        return Response(PolicyTableSerializer(policies, context={"user": request.user}, many=True).data)

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
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicySerializer(policy).data)

    def put(self, request, pk):
        from .tasks import generate_agent_checks_task

        policy = get_object_or_404(Policy, pk=pk)

        serializer = PolicySerializer(instance=policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # check for excluding objects and in the request and if present generate policies
        if (
            "excluded_sites" in request.data.keys()
            or "excluded_clients" in request.data.keys()
            or "excluded_agents" in request.data.keys()
        ):
            generate_agent_checks_task.delay(policy=pk, create_tasks=True)

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(Policy, pk=pk).delete()

        return Response("ok")


class PolicySync(APIView):
    def post(self, request):
        if "policy" in request.data.keys():
            from automation.tasks import generate_agent_checks_task

            generate_agent_checks_task.delay(
                policy=request.data["policy"], create_tasks=True
            )
            return Response("ok")

        else:
            return notify_error("The request was invalid")


class PolicyAutoTask(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]
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
        from .tasks import run_win_policy_autotasks_task

        run_win_policy_autotasks_task.delay(task=task)
        return Response("Affected agent tasks will run shortly")


class PolicyCheck(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

    def patch(self, request, check):
        checks = Check.objects.filter(parent_check=check)
        return Response(PolicyCheckStatusSerializer(checks, many=True).data)


class OverviewPolicy(APIView):
    def get(self, request):

        clients = Client.objects.all()
        return Response(PolicyOverviewSerializer(clients, many=True).data)


class GetRelated(APIView):
    def get(self, request, pk):

        policy = (
            Policy.objects.filter(pk=pk)
            .prefetch_related(
                "workstation_clients",
                "workstation_sites",
                "server_clients",
                "server_sites",
            )
            .first()
        )

        return Response(PolicyRelatedSerializer(policy, context={"user": request.user}).data)


class UpdatePatchPolicy(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]
    # create new patch policy
    def post(self, request):
        policy = get_object_or_404(Policy, pk=request.data["policy"])

        serializer = WinUpdatePolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.policy = policy  # type: ignore
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
