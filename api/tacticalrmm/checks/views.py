from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from agents.models import Agent
from automation.models import Policy

from .models import Check
from scripts.models import Script

from .serializers import CheckSerializer

from .tasks import handle_check_email_alert_task, run_checks_task
from autotasks.tasks import delete_win_task_schedule

from automation.tasks import (
    generate_agent_checks_from_policies_task, 
    delete_policy_check_task,
    update_policy_check_fields_task
)


class GetAddCheck(APIView):
    def get(self, request):
        checks = Check.objects.all()
        return Response(CheckSerializer(checks, many=True).data)

    def post(self, request):
        policy = None
        agent = None

        # Determine if adding check to Policy or Agent
        if "policy" in request.data:
            policy = get_object_or_404(Policy, id=request.data["policy"])
            # Object used for filter and save
            parent = {"policy": policy}
        else:
            agent = get_object_or_404(Agent, pk=request.data["pk"])
            parent = {"agent": agent}

        script = None
        if "script" in request.data["check"]:
            script = get_object_or_404(Script, pk=request.data["check"]["script"])

        serializer = CheckSerializer(
            data=request.data["check"], partial=True, context=parent
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(**parent, script=script)

        # Generate policy Checks
        if policy:
            generate_agent_checks_from_policies_task.delay(policypk=policy.pk)
        elif agent:
            agent.generate_checks_from_policies()

        return Response(f"{obj.readable_desc} was added!")


class GetUpdateDeleteCheck(APIView):
    def get(self, request, pk):
        check = get_object_or_404(Check, pk=pk)
        return Response(CheckSerializer(check).data)

    def patch(self, request, pk):
        check = get_object_or_404(Check, pk=pk)

        # remove fields that should not be changed when editing a check from the frontend
        if "check_alert" not in request.data.keys():
            [request.data.pop(i) for i in check.non_editable_fields]

        serializer = CheckSerializer(instance=check, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        # Update policy check fields
        if check.policy:
            update_policy_check_fields_task(checkpk=pk)

        return Response(f"{obj.readable_desc} was edited!")

    def delete(self, request, pk):
        check = get_object_or_404(Check, pk=pk)

        # Policy check deleted
        if check.policy:
            delete_policy_check_task.delay(checkpk=check.pk)

            # Re-evaluate agent checks is policy was enforced
            if check.policy.enforced:
                generate_agent_checks_from_policies_task.delay(policypk=check.policy.pk)

        # Agent check deleted
        elif check.agent:
            check.agent.generate_checks_from_policies()

        check.delete()
        
        return Response(f"{check.readable_desc} was deleted!")


@api_view()
def run_checks(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    run_checks_task.delay(agent.pk)
    return Response(agent.hostname)


@api_view()
def load_checks(request, pk):
    checks = Check.objects.filter(agent__pk=pk)
    return Response(CheckSerializer(checks, many=True).data)


@api_view()
def get_disks_for_policies(request):
    return Response(Check.all_disks())
