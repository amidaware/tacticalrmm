import asyncio
from typing import Any

from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents.models import Agent
from .models import ChocoSoftware, InstalledSoftware
from .serializers import InstalledSoftwareSerializer, ChocoSoftwareSerializer
from .tasks import install_program
from tacticalrmm.utils import notify_error, filter_software


@api_view()
def chocos(request):
    chocos = ChocoSoftware.objects.last()
    return Response(ChocoSoftwareSerializer(chocos).data["chocos"])


@api_view(["POST"])
def install(request):
    pk = request.data["pk"]
    agent = get_object_or_404(Agent, pk=pk)
    name = request.data["name"]
    version = request.data["version"]
    install_program.delay(pk, name, version)
    return Response(f"{name} will be installed shortly on {agent.hostname}")


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
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")

    r: Any = asyncio.run(agent.nats_cmd({"func": "softwarelist"}, timeout=15))
    if r == "timeout" or r == "natsdown":
        return notify_error("Unable to contact the agent")

    sw = filter_software(r)

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=sw).save()
    else:
        s = agent.installedsoftware_set.first()
        s.software = sw
        s.save(update_fields=["software"])

    return Response("ok")
