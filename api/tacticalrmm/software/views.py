import asyncio
from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from logs.models import PendingAction
from tacticalrmm.constants import PAAction
from tacticalrmm.helpers import notify_error

from .models import ChocoSoftware, InstalledSoftware
from .permissions import SoftwarePerms
from .serializers import InstalledSoftwareSerializer


@api_view(["GET"])
def chocos(request):
    chocos = ChocoSoftware.objects.last()
    if not chocos:
        return Response({})

    return Response(chocos.chocos)


class GetSoftware(APIView):
    permission_classes = [IsAuthenticated, SoftwarePerms]

    # get software list
    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)

            try:
                software = InstalledSoftware.objects.filter(agent=agent).get()
                return Response(InstalledSoftwareSerializer(software).data)
            except Exception:
                return Response([])
        else:
            software = InstalledSoftware.objects.filter_by_role(request.user)  # type: ignore
            return Response(InstalledSoftwareSerializer(software, many=True).data)

    # software install
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        if agent.is_posix:
            return notify_error(f"Not available for {agent.plat}")

        name = request.data["name"]

        action = PendingAction.objects.create(
            agent=agent,
            action_type=PAAction.CHOCO_INSTALL,
            details={"name": name, "output": None, "installed": False},
        )

        nats_data = {
            "func": "installwithchoco",
            "choco_prog_name": name,
            "pending_action_pk": action.pk,
        }

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=2))
        if r != "ok":
            action.delete()
            return notify_error("Unable to contact the agent")

        return Response(
            f"{name} will be installed shortly on {agent.hostname}. Check the Pending Actions menu to see the status/output"
        )

    # refresh software list
    def put(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        if agent.is_posix:
            return notify_error(f"Not available for {agent.plat}")

        r: Any = asyncio.run(agent.nats_cmd({"func": "softwarelist"}, timeout=15))
        if r in ("timeout", "natsdown"):
            return notify_error("Unable to contact the agent")

        if not InstalledSoftware.objects.filter(agent=agent).exists():
            InstalledSoftware(agent=agent, software=r).save()
        else:
            s = agent.installedsoftware_set.first()  # type: ignore
            s.software = r
            s.save(update_fields=["software"])

        return Response("ok")
