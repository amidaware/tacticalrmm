import asyncio
from typing import Any

from django.shortcuts import get_object_or_404
from packaging import version as pyver
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from agents.models import Agent
from logs.models import PendingAction
from tacticalrmm.utils import filter_software, notify_error

from .models import ChocoSoftware, InstalledSoftware
from .permissions import ManageSoftwarePerms
from .serializers import InstalledSoftwareSerializer


@api_view()
def chocos(request):
    return Response(ChocoSoftware.objects.last().chocos)


@api_view(["POST"])
@permission_classes([IsAuthenticated, ManageSoftwarePerms])
def install(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if pyver.parse(agent.version) < pyver.parse("1.4.8"):
        return notify_error("Requires agent v1.4.8")

    name = request.data["name"]

    action = PendingAction.objects.create(
        agent=agent,
        action_type="chocoinstall",
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


@api_view()
def get_installed(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    try:
        software = InstalledSoftware.objects.filter(agent=agent).get()
    except Exception:
        return Response([])
    else:
        return Response(InstalledSoftwareSerializer(software).data)


@api_view()
def refresh_installed(request, pk):
    agent = get_object_or_404(Agent, pk=pk)

    r: Any = asyncio.run(agent.nats_cmd({"func": "softwarelist"}, timeout=15))
    if r == "timeout" or r == "natsdown":
        return notify_error("Unable to contact the agent")

    sw = filter_software(r)

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=sw).save()
    else:
        s = agent.installedsoftware_set.first()  # type: ignore
        s.software = sw
        s.save(update_fields=["software"])

    return Response("ok")
