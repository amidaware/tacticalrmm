import asyncio

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from agents.models import Agent
from tacticalrmm.utils import get_default_timezone

from .models import WinUpdate
from .permissions import ManageWinUpdatePerms
from .serializers import UpdateSerializer


@api_view()
def get_win_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    ctx = {"default_tz": get_default_timezone()}
    serializer = UpdateSerializer(agent, context=ctx)
    return Response(serializer.data)


@api_view()
@permission_classes([IsAuthenticated, ManageWinUpdatePerms])
def run_update_scan(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    agent.delete_superseded_updates()
    asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
    return Response("ok")


@api_view()
@permission_classes([IsAuthenticated, ManageWinUpdatePerms])
def install_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    agent.delete_superseded_updates()
    agent.approve_updates()
    nats_data = {
        "func": "installwinupdates",
        "guids": agent.get_approved_update_guids(),
    }
    asyncio.run(agent.nats_cmd(nats_data, wait=False))
    return Response(f"Patches will now be installed on {agent.hostname}")


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, ManageWinUpdatePerms])
def edit_policy(request):
    patch = get_object_or_404(WinUpdate, pk=request.data["pk"])
    patch.action = request.data["policy"]
    patch.save(update_fields=["action"])
    return Response("ok")
