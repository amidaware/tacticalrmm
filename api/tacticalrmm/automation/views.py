from agents.models import Agent
from autotasks.models import TaskResult
from checks.models import CheckResult
from clients.models import Client
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from winupdate.models import WinUpdatePolicy
from winupdate.serializers import WinUpdatePolicySerializer

from tacticalrmm.permissions import _has_perm_on_client, _has_perm_on_site

from .models import Policy
from .permissions import AutomationPolicyPerms
from .serializers import (
    PolicyCheckStatusSerializer,
    PolicyOverviewSerializer,
    PolicyRelatedSerializer,
    PolicySerializer,
    PolicyTableSerializer,
    PolicyTaskStatusSerializer,
)


class GetAddPolicies(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

    def get(self, request):
        policies = Policy.objects.all()

        return Response(
            PolicyTableSerializer(
                policies, context={"user": request.user}, many=True
            ).data
        )

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
                if not task.assigned_check:
                    task.create_policy_task(policy=policy)

        return Response("ok")


class GetUpdateDeletePolicy(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

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

    # get status of all tasks
    def get(self, request, task):
        tasks = TaskResult.objects.filter(task=task)
        return Response(PolicyTaskStatusSerializer(tasks, many=True).data)

    # bulk run win tasks associated with policy
    def post(self, request, task):
        from .tasks import run_win_policy_autotasks_task

        run_win_policy_autotasks_task.delay(task=task)
        return Response("Affected agent tasks will run shortly")


class PolicyCheck(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]

    def get(self, request, check):
        checks = CheckResult.objects.filter(assigned_check=check)
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

        return Response(
            PolicyRelatedSerializer(policy, context={"user": request.user}).data
        )


class UpdatePatchPolicy(APIView):
    permission_classes = [IsAuthenticated, AutomationPolicyPerms]
    # create new patch policy
    def post(self, request):
        policy = get_object_or_404(Policy, pk=request.data["policy"])

        serializer = WinUpdatePolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.policy = policy
        serializer.save()

        return Response("ok")

    # update patch policy
    def put(self, request, pk):
        policy = get_object_or_404(WinUpdatePolicy, pk=pk)

        serializer = WinUpdatePolicySerializer(
            instance=policy, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    # delete patch policy
    def delete(self, request, pk):
        get_object_or_404(WinUpdatePolicy, pk=pk).delete()

        return Response("ok")


class ResetPatchPolicy(APIView):
    # bulk reset agent patch policy
    def post(self, request):

        if "client" in request.data:
            if not _has_perm_on_client(request.user, request.data["client"]):
                raise PermissionDenied()

            agents = (
                Agent.objects.filter_by_role(request.user)  # type: ignore
                .prefetch_related("winupdatepolicy")
                .filter(site__client_id=request.data["client"])
            )
        elif "site" in request.data:
            if not _has_perm_on_site(request.user, request.data["site"]):
                raise PermissionDenied()

            agents = (
                Agent.objects.filter_by_role(request.user)  # type: ignore
                .prefetch_related("winupdatepolicy")
                .filter(site_id=request.data["site"])
            )
        else:
            agents = (
                Agent.objects.filter_by_role(request.user)  # type: ignore
                .prefetch_related("winupdatepolicy")
                .only("pk")
            )

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

        return Response("The patch policy on the affected agents has been reset.")
