import asyncio
import time
from typing import List

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from loguru import logger
from packaging import version as pyver
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.serializers import WinAgentSerializer
from agents.tasks import (
    agent_recovery_email_task,
    agent_recovery_sms_task,
    handle_agent_recovery_task,
)
from checks.utils import bytes2human
from software.models import InstalledSoftware
from tacticalrmm.utils import SoftwareList, filter_software, notify_error
from winupdate.models import WinUpdate

logger.configure(**settings.LOG_CONFIG)


@api_view()
@permission_classes([])
@authentication_classes([])
def nats_info(request):
    return Response({"user": "tacticalrmm", "password": settings.SECRET_KEY})


class NatsCheckIn(APIView):

    authentication_classes = []
    permission_classes = []

    def patch(self, request):
        updated = False
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if pyver.parse(request.data["version"]) > pyver.parse(
            agent.version
        ) or pyver.parse(request.data["version"]) == pyver.parse(
            settings.LATEST_AGENT_VER
        ):
            updated = True
        agent.version = request.data["version"]
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["version", "last_seen"])

        # change agent update pending status to completed if agent has just updated
        if (
            updated
            and agent.pendingactions.filter(
                action_type="agentupdate", status="pending"
            ).exists()
        ):
            agent.pendingactions.filter(
                action_type="agentupdate", status="pending"
            ).update(status="completed")

        # handles any alerting actions
        agent.handle_alert(checkin=True)

        recovery = agent.recoveryactions.filter(last_run=None).last()
        if recovery is not None:
            recovery.last_run = djangotime.now()
            recovery.save(update_fields=["last_run"])
            handle_agent_recovery_task.delay(pk=recovery.pk)
            return Response("ok")

        # get any pending actions
        if agent.pendingactions.filter(status="pending").exists():
            agent.handle_pending_actions()

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

    # called once during tacticalagent windows service startup
    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if not agent.choco_installed:
            asyncio.run(agent.nats_cmd({"func": "installchoco"}, wait=False))

        time.sleep(0.5)
        asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
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


class NatsChoco(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        agent.choco_installed = request.data["installed"]
        agent.save(update_fields=["choco_installed"])
        return Response("ok")


class NatsWinUpdates(APIView):
    authentication_classes = []
    permission_classes = []

    def put(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        reboot_policy: str = agent.get_patch_policy().reboot_after_install
        reboot = False

        if reboot_policy == "always":
            reboot = True

        if request.data["needs_reboot"]:
            if reboot_policy == "required":
                reboot = True
            elif reboot_policy == "never":
                agent.needs_reboot = True
                agent.save(update_fields=["needs_reboot"])

        if reboot:
            asyncio.run(agent.nats_cmd({"func": "rebootnow"}, wait=False))
            logger.info(f"{agent.hostname} is rebooting after updates were installed.")

        agent.delete_superseded_updates()
        return Response("ok")

    def patch(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        u = agent.winupdates.filter(guid=request.data["guid"]).last()
        success: bool = request.data["success"]
        if success:
            u.result = "success"
            u.downloaded = True
            u.installed = True
            u.date_installed = djangotime.now()
            u.save(
                update_fields=[
                    "result",
                    "downloaded",
                    "installed",
                    "date_installed",
                ]
            )
        else:
            u.result = "failed"
            u.save(update_fields=["result"])

        agent.delete_superseded_updates()
        return Response("ok")

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        updates = request.data["wua_updates"]
        for update in updates:
            if agent.winupdates.filter(guid=update["guid"]).exists():
                u = agent.winupdates.filter(guid=update["guid"]).last()
                u.downloaded = update["downloaded"]
                u.installed = update["installed"]
                u.save(update_fields=["downloaded", "installed"])
            else:
                try:
                    kb = "KB" + update["kb_article_ids"][0]
                except:
                    continue

                WinUpdate(
                    agent=agent,
                    guid=update["guid"],
                    kb=kb,
                    title=update["title"],
                    installed=update["installed"],
                    downloaded=update["downloaded"],
                    description=update["description"],
                    severity=update["severity"],
                    categories=update["categories"],
                    category_ids=update["category_ids"],
                    kb_article_ids=update["kb_article_ids"],
                    more_info_urls=update["more_info_urls"],
                    support_url=update["support_url"],
                    revision_number=update["revision_number"],
                ).save()

        agent.delete_superseded_updates()

        # more superseded updates cleanup
        if pyver.parse(agent.version) <= pyver.parse("1.4.2"):
            for u in agent.winupdates.filter(
                date_installed__isnull=True, result="failed"
            ).exclude(installed=True):
                u.delete()

        return Response("ok")


class SupersededWinUpdate(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        updates = agent.winupdates.filter(guid=request.data["guid"])
        for u in updates:
            u.delete()

        return Response("ok")


class NatsWMI(APIView):

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        agents = Agent.objects.only(
            "pk", "agent_id", "version", "last_seen", "overdue_time", "offline_time"
        )
        online: List[str] = [
            i.agent_id
            for i in agents
            if pyver.parse(i.version) >= pyver.parse("1.2.0") and i.status == "online"
        ]
        return Response({"agent_ids": online})


class OfflineAgents(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        agents = Agent.objects.only(
            "pk", "agent_id", "version", "last_seen", "overdue_time", "offline_time"
        )
        offline: List[str] = [
            i.agent_id for i in agents if i.has_nats and i.status != "online"
        ]
        return Response({"agent_ids": offline})


class LogCrash(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agentid"])
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["last_seen"])
        return Response("ok")
