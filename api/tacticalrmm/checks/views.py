from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from tacticalrmm.utils import notify_error
from agents.models import Agent
from automation.models import Policy

from .models import Check
from scripts.models import Script

from .serializers import CheckSerializer

from .tasks import run_checks_task

from automation.tasks import (
    generate_agent_checks_from_policies_task,
    delete_policy_check_task,
    update_policy_check_fields_task,
)


class AddCheck(APIView):
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
            added = "0.11.0"
            if (
                request.data["check"]["check_type"] == "script"
                and request.data["check"]["script_args"]
                and agent.not_supported(version_added=added)
            ):
                return notify_error(
                    {
                        "non_field_errors": f"Script arguments only available in agent {added} or greater"
                    }
                )

        script = None
        if "script" in request.data["check"]:
            script = get_object_or_404(Script, pk=request.data["check"]["script"])

        # set event id to 0 if wildcard because it needs to be an integer field for db
        # will be ignored anyway by the agent when doing wildcard check
        if (
            request.data["check"]["check_type"] == "eventlog"
            and request.data["check"]["event_id_is_wildcard"]
        ):
            if agent and agent.not_supported(version_added="0.10.2"):
                return notify_error(
                    {
                        "non_field_errors": "Wildcard is only available in agent 0.10.2 or greater"
                    }
                )

            request.data["check"]["event_id"] = 0

        serializer = CheckSerializer(
            data=request.data["check"], partial=True, context=parent
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(**parent, script=script)

        # Generate policy Checks
        if policy:
            generate_agent_checks_from_policies_task.delay(policypk=policy.pk)
        elif agent:
            checks = agent.agentchecks.filter(
                check_type=obj.check_type, managed_by_policy=True
            )

            # Should only be one
            duplicate_check = [check for check in checks if check.is_duplicate(obj)]

            if duplicate_check:
                policy = Check.objects.get(pk=duplicate_check[0].parent_check).policy
                if policy.enforced:
                    obj.overriden_by_policy = True
                    obj.save()
                else:
                    duplicate_check[0].delete()

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

        # set event id to 0 if wildcard because it needs to be an integer field for db
        # will be ignored anyway by the agent when doing wildcard check
        if check.check_type == "eventlog":
            try:
                request.data["event_id_is_wildcard"]
            except KeyError:
                pass
            else:
                if request.data["event_id_is_wildcard"]:
                    if check.agent.not_supported(version_added="0.10.2"):
                        return notify_error(
                            {
                                "non_field_errors": "Wildcard is only available in agent 0.10.2 or greater"
                            }
                        )

                    request.data["event_id"] = 0

        elif check.check_type == "script":
            added = "0.11.0"
            try:
                request.data["script_args"]
            except KeyError:
                pass
            else:
                if request.data["script_args"] and check.agent.not_supported(
                    version_added=added
                ):
                    return notify_error(
                        {
                            "non_field_errors": f"Script arguments only available in agent {added} or greater"
                        }
                    )

        serializer = CheckSerializer(instance=check, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        # Update policy check fields
        if check.policy:
            update_policy_check_fields_task(checkpk=pk)

        return Response(f"{obj.readable_desc} was edited!")

    def delete(self, request, pk):
        check = get_object_or_404(Check, pk=pk)

        check_pk = check.pk
        policy_pk = None
        if check.policy:
            policy_pk = check.policy.pk

        check.delete()

        # Policy check deleted
        if check.policy:
            delete_policy_check_task.delay(checkpk=check_pk)

            # Re-evaluate agent checks is policy was enforced
            if check.policy.enforced:
                generate_agent_checks_from_policies_task.delay(policypk=policy_pk)

        # Agent check deleted
        elif check.agent:
            check.agent.generate_checks_from_policies()

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
