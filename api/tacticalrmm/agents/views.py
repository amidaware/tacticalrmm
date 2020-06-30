from loguru import logger
import subprocess
from packaging import version as pyver
import zlib
import json
import base64
import datetime as dt

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authentication import BasicAuthentication, TokenAuthentication

from .models import Agent
from winupdate.models import WinUpdatePolicy
from clients.models import Client, Site
from accounts.models import User
from core.models import CoreSettings

from .serializers import AgentSerializer, AgentHostnameSerializer, AgentTableSerializer
from winupdate.serializers import WinUpdatePolicySerializer

from .tasks import uninstall_agent_task, update_agent_task

from tacticalrmm.utils import notify_error

logger.configure(**settings.LOG_CONFIG)


@api_view()
def get_agent_versions(request):
    agents = Agent.objects.only("pk")
    ret = Agent.get_github_versions()
    return Response(
        {
            "versions": ret["versions"],
            "github": ret["data"],
            "agents": AgentHostnameSerializer(agents, many=True).data,
        }
    )


@api_view(["POST"])
def update_agents(request):
    pks = request.data["pks"]
    version = request.data["version"]
    ver = version.split("winagent-v")[1]
    agents = Agent.objects.filter(pk__in=pks)

    for agent in agents:
        # don't update if agent's version same or higher
        if (
            not pyver.parse(agent.version) >= pyver.parse(ver)
        ) and not agent.is_updating:
            agent.is_updating = True
            agent.save(update_fields=["is_updating"])

            update_agent_task.apply_async(
                queue="wupdate", kwargs={"pk": agent.pk, "version": version}
            )

    return Response("ok")


@api_view()
def ping(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=5, func="test.ping")

    if r == "timeout" or r == "error":
        return Response({"name": agent.hostname, "status": "offline"})

    if isinstance(r, bool) and r:
        return Response({"name": agent.hostname, "status": "online"})
    else:
        return Response({"name": agent.hostname, "status": "offline"})


@api_view(["DELETE"])
def uninstall(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    user = get_object_or_404(User, username=agent.agent_id)
    salt_id = agent.salt_id
    name = agent.hostname
    user.delete()
    agent.delete()

    uninstall_agent_task.delay(salt_id)
    return Response(f"{name} will now be uninstalled.")


@api_view(["PATCH"])
def edit_agent(request):
    agent = get_object_or_404(Agent, pk=request.data["id"])
    a_serializer = AgentSerializer(instance=agent, data=request.data, partial=True)
    a_serializer.is_valid(raise_exception=True)
    a_serializer.save()

    policy = WinUpdatePolicy.objects.get(agent=agent)
    p_serializer = WinUpdatePolicySerializer(
        instance=policy, data=request.data["winupdatepolicy"][0]
    )
    p_serializer.is_valid(raise_exception=True)
    p_serializer.save()

    return Response("ok")


@api_view()
def meshcentral(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    core = CoreSettings.objects.first()

    token = agent.get_login_token(
        key=core.mesh_token, user=f"user//{core.mesh_username}"
    )

    if token == "err":
        return notify_error("Invalid mesh token")

    control = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=11&hide=31"
    )
    terminal = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=12&hide=31"
    )
    file = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=13&hide=31"
    )
    webrdp = f"{core.mesh_site}/mstsc.html?login={token}&node={agent.mesh_node_id}"

    ret = {
        "hostname": agent.hostname,
        "control": control,
        "terminal": terminal,
        "file": file,
        "webrdp": webrdp,
    }
    return Response(ret)


@api_view()
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentSerializer(agent).data)


@api_view()
def get_processes(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=20, func="win_agent.get_procs")

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")

    return Response(r)


@api_view()
def kill_proc(request, pk, pid):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=25, func="ps.kill_pid", arg=int(pid))

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")

    if isinstance(r, bool) and not r:
        return notify_error("Unable to kill the process")

    return Response("ok")


@api_view()
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(
        timeout=30, func="win_agent.get_eventlog", arg=[logtype, int(days)],
    )

    if r == "timeout" or r == "error":
        return notify_error("Unable to contact the agent")

    return Response(json.loads(zlib.decompress(base64.b64decode(r["wineventlog"]))))


@api_view(["POST"])
def power_action(request):
    pk = request.data["pk"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if action == "rebootnow":
        logger.info(f"{agent.hostname} was scheduled for immediate reboot")
        r = agent.salt_api_cmd(
            timeout=30, func="system.reboot", arg=3, kwargs={"in_seconds": True},
        )
    if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
        return notify_error("Unable to contact the agent")

    return Response("ok")


@api_view(["POST"])
def send_raw_cmd(request):
    pk = request.data["pk"]
    cmd = request.data["rawcmd"]
    if not cmd:
        return notify_error("Please enter a command")

    agent = get_object_or_404(Agent, pk=pk)
    # TODO add timeout to frontend
    r = agent.salt_api_cmd(timeout=30, func="cmd.run", arg=cmd)
    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    logger.info(f"The command {cmd} was sent on agent {agent.hostname}")
    return Response(r)


@api_view()
def list_agents(request):
    agents = Agent.objects.all()
    return Response(AgentTableSerializer(agents, many=True).data)


@api_view()
def list_agents_no_detail(request):
    agents = Agent.objects.all()
    return Response(AgentHostnameSerializer(agents, many=True).data)


@api_view()
def by_client(request, client):
    agents = Agent.objects.filter(client=client)
    return Response(AgentTableSerializer(agents, many=True).data)


@api_view()
def by_site(request, client, site):
    agents = Agent.objects.filter(client=client).filter(site=site)
    return Response(AgentTableSerializer(agents, many=True).data)


@api_view(["POST"])
def overdue_action(request):
    pk = request.data["pk"]
    alert_type = request.data["alertType"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if alert_type == "email" and action == "enabled":
        agent.overdue_email_alert = True
        agent.save(update_fields=["overdue_email_alert"])
    elif alert_type == "email" and action == "disabled":
        agent.overdue_email_alert = False
        agent.save(update_fields=["overdue_email_alert"])
    elif alert_type == "text" and action == "enabled":
        agent.overdue_text_alert = True
        agent.save(update_fields=["overdue_text_alert"])
    elif alert_type == "text" and action == "disabled":
        agent.overdue_text_alert = False
        agent.save(update_fields=["overdue_text_alert"])
    else:
        return Response(
            {"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(agent.hostname)


@api_view(["POST"])
def reboot_later(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    date_time = request.data["datetime"]

    try:
        obj = dt.datetime.strptime(date_time, "%Y-%m-%d %H:%M")
    except Exception:
        return notify_error("Invalid date")

    r = agent.schedule_reboot(obj)

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "failed":
        return notify_error("Something went wrong")

    return Response(r["msg"])


@api_view(["POST"])
def install_agent(request):
    from knox.models import AuthToken

    client = get_object_or_404(Client, client=request.data["client"])
    site = get_object_or_404(Site, client=client, site=request.data["site"])

    _, token = AuthToken.objects.create(user=request.user, expiry=dt.timedelta(hours=1))

    resp = {"token": token, "client": client.pk, "site": site.pk}
    return Response(resp)
