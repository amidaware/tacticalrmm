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

from .serializers import AgentSerializer, AgentHostnameSerializer, AgentTableSerializer
from winupdate.serializers import WinUpdatePolicySerializer

from .tasks import uninstall_agent_task, update_agent_task

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
    try:
        r = agent.salt_api_cmd(hostname=agent.salt_id, timeout=5, func="test.ping")
    except Exception:
        return Response({"name": agent.hostname, "status": "offline"})

    data = r.json()["return"][0][agent.salt_id]
    if isinstance(data, bool) and data:
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
def meshcentral_tabs(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    token = agent.get_login_token(
        key=settings.MESH_TOKEN_KEY, user=f"user//{settings.MESH_USERNAME}"
    )
    terminalurl = f"{settings.MESH_SITE}/?login={token}&node={agent.mesh_node_id}&viewmode=12&hide=31"
    fileurl = f"{settings.MESH_SITE}/?login={token}&node={agent.mesh_node_id}&viewmode=13&hide=31"
    return Response(
        {"hostname": agent.hostname, "terminalurl": terminalurl, "fileurl": fileurl}
    )


@api_view()
def take_control(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    token = agent.get_login_token(
        key=settings.MESH_TOKEN_KEY, user=f"user//{settings.MESH_USERNAME}"
    )
    url = f"{settings.MESH_SITE}/?login={token}&node={agent.mesh_node_id}&viewmode=11&hide=31"
    return Response(url)


@api_view()
def web_rdp(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    token = agent.get_login_token(
        key=settings.MESH_TOKEN_KEY, user=f"user//{settings.MESH_USERNAME}"
    )
    url = f"{settings.MESH_SITE}/mstsc.html?login={token}&node={agent.mesh_node_id}"
    return Response(url)


@api_view()
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentSerializer(agent).data)


@api_view()
def get_processes(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.salt_id, timeout=70, func="win_agent.get_procs"
        )
        data = resp.json()
    except Exception:
        return Response(
            {"error": "unable to contact the agent"}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(data["return"][0][agent.salt_id])


@api_view()
def kill_proc(request, pk, pid):
    agent = get_object_or_404(Agent, pk=pk)
    resp = agent.salt_api_cmd(
        hostname=agent.salt_id, timeout=60, func="ps.kill_pid", arg=int(pid)
    )
    data = resp.json()

    if not data["return"][0][agent.salt_id]:
        return Response(
            {"error": "Unable to kill the process"}, status=status.HTTP_400_BAD_REQUEST
        )
    else:
        return Response("ok")


@api_view()
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.salt_id,
            timeout=90,
            salt_timeout=85,
            func="win_agent.get_eventlog",
            arg=[logtype, int(days)],
        )
    except Exception:
        return Response("Agent timed out", status=status.HTTP_400_BAD_REQUEST)

    return Response(
        json.loads(
            zlib.decompress(
                base64.b64decode(resp.json()["return"][0][agent.salt_id]["wineventlog"])
            )
        )
    )


@api_view(["POST"])
def power_action(request):
    pk = request.data["pk"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if action == "rebootnow":
        logger.info(f"{agent.hostname} was scheduled for immediate reboot")
        resp = agent.salt_api_cmd(
            hostname=agent.salt_id,
            timeout=30,
            func="system.reboot",
            arg=3,
            kwargs={"in_seconds": True},
        )

    data = resp.json()
    if not data["return"][0][agent.salt_id]:
        return Response(
            "unable to contact the agent", status=status.HTTP_400_BAD_REQUEST
        )

    return Response("ok")


@api_view(["POST"])
def send_raw_cmd(request):
    pk = request.data["pk"]
    cmd = request.data["rawcmd"]
    if not cmd:
        return Response("please enter a command", status=status.HTTP_400_BAD_REQUEST)

    agent = get_object_or_404(Agent, pk=pk)
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.salt_id, timeout=60, func="cmd.run", arg=cmd
        )
        data = resp.json()
    except Exception:
        return Response(
            "unable to contact the agent", status=status.HTTP_400_BAD_REQUEST
        )

    if not data["return"][0][agent.salt_id]:
        return Response(
            "unable to contact the agent", status=status.HTTP_400_BAD_REQUEST
        )
    logger.info(f"The command {cmd} was sent on agent {agent.hostname}")
    return Response(data["return"][0][agent.salt_id])


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
        return Response("invalid date", status=status.HTTP_400_BAD_REQUEST)

    resp = agent.schedule_reboot(obj)

    if resp["ret"] and resp["success"]:
        return Response(resp["msg"])
    elif resp["ret"] and not resp["success"]:
        return Response(resp["msg"], status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(resp["msg"], status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def install_agent(request):
    from knox.models import AuthToken

    client = get_object_or_404(Client, client=request.data["client"])
    site = get_object_or_404(Site, client=client, site=request.data["site"])

    _, token = AuthToken.objects.create(user=request.user, expiry=dt.timedelta(hours=1))

    resp = {"token": token, "client": client.pk, "site": site.pk}
    return Response(resp)
