from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from rest_framework.response import Response
from rest_framework import status

from agents.models import Agent
from .models import ChocoSoftware, InstalledSoftware
from .serializers import ChocoSoftwareSerializer, InstalledSoftwareSerializer
from .tasks import install_program


@api_view()
def chocos(request):
    return Response(ChocoSoftware.combine_all())


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
    r = agent.salt_api_cmd(hostname=agent.salt_id, timeout=30, func="pkg.list_pkgs")
    try:
        output = r.json()["return"][0][agent.salt_id]
    except Exception:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)

    try:
        software = [{"name": k, "version": v} for k, v in output.items()]
    except Exception:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=software).save()
    else:
        current = InstalledSoftware.objects.filter(agent=agent).get()
        current.software = software
        current.save(update_fields=["software"])

    return Response("ok")
