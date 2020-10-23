from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from agents.models import Agent
from .models import WinUpdate
from .serializers import UpdateSerializer, ApprovedUpdateSerializer
from .tasks import check_for_updates_task
from tacticalrmm.utils import notify_error


@api_view()
def get_win_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(UpdateSerializer(agent).data)


@api_view()
def run_update_scan(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    check_for_updates_task.apply_async(
        queue="wupdate", kwargs={"pk": agent.pk, "wait": False, "auto_approve": True}
    )
    return Response("ok")


@api_view()
def install_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=15, func="win_agent.install_updates")

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")
    elif r == "running":
        return notify_error(f"Updates are already being installed on {agent.hostname}")

    # successful response: {'return': [{'SALT-ID': {'pid': 3316}}]}
    try:
        r["pid"]
    except (KeyError):
        return notify_error(str(r))

    return Response(f"Patches will now be installed on {agent.hostname}")


@api_view(["PATCH"])
def edit_policy(request):
    patch = get_object_or_404(WinUpdate, pk=request.data["pk"])
    patch.action = request.data["policy"]
    patch.save(update_fields=["action"])
    return Response("ok")


@api_view()
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def win_updater(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
    agent.delete_superseded_updates()
    patches = (
        WinUpdate.objects.filter(agent=agent)
        .exclude(installed=True)
        .filter(action="approve")
    )
    if patches:
        return Response(ApprovedUpdateSerializer(patches, many=True).data)

    return Response("nopatches")