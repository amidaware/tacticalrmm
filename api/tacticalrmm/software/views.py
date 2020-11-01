import string

from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents.models import Agent
from .models import ChocoSoftware, InstalledSoftware
from .serializers import InstalledSoftwareSerializer
from .tasks import install_program
from tacticalrmm.utils import notify_error


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
    r = agent.salt_api_cmd(
        timeout=20,
        func="pkg.list_pkgs",
        kwargs={"include_components": False, "include_updates": False},
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")

    printable = set(string.printable)

    try:
        software = [
            {
                "name": "".join(filter(lambda x: x in printable, k)),
                "version": "".join(filter(lambda x: x in printable, v)),
            }
            for k, v in r.items()
        ]
    except Exception:
        return notify_error("Something went wrong")

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=software).save()
    else:
        s = agent.installedsoftware_set.get()
        s.software = software
        s.save(update_fields=["software"])

    return Response("ok")
