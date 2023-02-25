import asyncio

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from tacticalrmm.helpers import notify_error
from tacticalrmm.permissions import _has_perm_on_agent
from tacticalrmm.utils import get_default_timezone

from .models import WinUpdate
from .permissions import AgentWinUpdatePerms
from .serializers import WinUpdateSerializer


class GetWindowsUpdates(APIView):
    permission_classes = [IsAuthenticated, AgentWinUpdatePerms]

    # list windows updates on agent
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        updates = WinUpdate.objects.filter(agent=agent).order_by("-id", "installed")
        ctx = {"default_tz": get_default_timezone()}
        serializer = WinUpdateSerializer(updates, many=True, context=ctx)
        return Response(serializer.data)


class ScanWindowsUpdates(APIView):
    permission_classes = [IsAuthenticated, AgentWinUpdatePerms]

    # scan for windows updates on agent
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        if agent.is_posix:
            return notify_error(f"Not available for {agent.plat}")

        agent.delete_superseded_updates()
        asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
        return Response(f"A Windows update scan will be performed on {agent.hostname}")


class InstallWindowsUpdates(APIView):
    permission_classes = [IsAuthenticated, AgentWinUpdatePerms]

    # install approved windows updates on agent
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        agent.delete_superseded_updates()
        agent.approve_updates()
        nats_data = {
            "func": "installwinupdates",
            "guids": agent.get_approved_update_guids(),
        }
        asyncio.run(agent.nats_cmd(nats_data, wait=False))
        return Response(f"Approved patches will now be installed on {agent.hostname}")


class EditWindowsUpdates(APIView):
    permission_classes = [IsAuthenticated, AgentWinUpdatePerms]

    # change approval status of update
    def put(self, request, pk):
        update = get_object_or_404(WinUpdate, pk=pk)

        if not _has_perm_on_agent(request.user, update.agent.agent_id):
            raise PermissionDenied()

        serializer = WinUpdateSerializer(
            instance=update, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(f"Windows update {update.kb} was changed to {update.action}")
