from django.utils import timezone as djangotime

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)

from django.conf import settings
from django.shortcuts import get_object_or_404

from agents.models import Agent
from software.models import InstalledSoftware
from checks.utils import bytes2human
from agents.serializers import WinAgentSerializer

from tacticalrmm.utils import notify_error, filter_software, SoftwareList


@api_view()
@permission_classes([])
@authentication_classes([])
def nats_info(request):
    return Response({"user": "tacticalrmm", "password": settings.SECRET_KEY})


class NatsCheckIn(APIView):

    authentication_classes = []
    permission_classes = []

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        agent.version = request.data["version"]
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["version", "last_seen"])
        return Response("ok")

    def put(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        serializer = WinAgentSerializer(instance=agent, data=request.data, partial=True)

        if request.data["func"] == "disks":
            disks = request.data["disks"]
            new = []
            for disk in disks:
                tmp = {}
                for _, _ in disk.items():
                    tmp["device"] = disk["device"]
                    tmp["fstype"] = disk["fstype"]
                    tmp["total"] = bytes2human(disk["total"])
                    tmp["used"] = bytes2human(disk["used"])
                    tmp["free"] = bytes2human(disk["free"])
                    tmp["percent"] = int(disk["percent"])
                new.append(tmp)

            serializer.is_valid(raise_exception=True)
            serializer.save(disks=new)
            return Response("ok")

        if request.data["func"] == "loggedonuser":
            if request.data["logged_in_username"] != "None":
                serializer.is_valid(raise_exception=True)
                serializer.save(last_logged_in_user=request.data["logged_in_username"])
                return Response("ok")

        if request.data["func"] == "software":
            raw: SoftwareList = request.data["software"]
            if not isinstance(raw, list):
                return notify_error("err")

            sw = filter_software(raw)
            if not InstalledSoftware.objects.filter(agent=agent).exists():
                InstalledSoftware(agent=agent, software=sw).save()
            else:
                s = agent.installedsoftware_set.first()
                s.software = sw
                s.save(update_fields=["software"])

            return Response("ok")

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class SyncMeshNodeID(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if agent.mesh_node_id != request.data["nodeid"]:
            agent.mesh_node_id = request.data["nodeid"]
            agent.save(update_fields=["mesh_node_id"])

        return Response("ok")
