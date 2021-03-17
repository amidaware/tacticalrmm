import asyncio
from datetime import datetime as dt

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from packaging import version as pyver
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from automation.models import Policy
from automation.tasks import (
    delete_policy_check_task,
    generate_agent_checks_from_policies_task,
    update_policy_check_fields_task,
)
from scripts.models import Script
from tacticalrmm.utils import notify_error

from .models import Check
from .serializers import CheckHistorySerializer, CheckSerializer


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

        script = None
        if "script" in request.data["check"]:
            script = get_object_or_404(Script, pk=request.data["check"]["script"])

        # set event id to 0 if wildcard because it needs to be an integer field for db
        # will be ignored anyway by the agent when doing wildcard check
        if (
            request.data["check"]["check_type"] == "eventlog"
            and request.data["check"]["event_id_is_wildcard"]
        ):
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
            checks = agent.agentchecks.filter(  # type: ignore
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
                    request.data["event_id"] = 0

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


class CheckHistory(APIView):
    def patch(self, request, checkpk):
        check = get_object_or_404(Check, pk=checkpk)

        timeFilter = Q()

        if "timeFilter" in request.data:
            if request.data["timeFilter"] != 0:
                timeFilter = Q(
                    x__lte=djangotime.make_aware(dt.today()),
                    x__gt=djangotime.make_aware(dt.today())
                    - djangotime.timedelta(days=request.data["timeFilter"]),
                )

        check_history = check.check_history.filter(timeFilter).order_by("-x")  # type: ignore

        return Response(
            CheckHistorySerializer(
                check_history, context={"timezone": check.agent.timezone}, many=True
            ).data
        )


@api_view()
def run_checks(request, pk):
    agent = get_object_or_404(Agent, pk=pk)

    if pyver.parse(agent.version) >= pyver.parse("1.4.1"):
        r = asyncio.run(agent.nats_cmd({"func": "runchecks"}, timeout=15))
        if r == "busy":
            return notify_error(f"Checks are already running on {agent.hostname}")
        elif r == "ok":
            return Response(f"Checks will now be re-run on {agent.hostname}")
        else:
            return notify_error("Unable to contact the agent")
    else:
        asyncio.run(agent.nats_cmd({"func": "runchecks"}, wait=False))
        return Response(f"Checks will now be re-run on {agent.hostname}")


@api_view()
def load_checks(request, pk):
    checks = Check.objects.filter(agent__pk=pk)
    return Response(CheckSerializer(checks, many=True).data)


@api_view()
def get_disks_for_policies(request):
    return Response(Check.all_disks())
