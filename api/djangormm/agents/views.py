from loguru import logger

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
from .serializers import AgentSerializer
from .tasks import uninstall_agent_task, update_agent_task

logger.configure(**settings.LOG_CONFIG)

@api_view()
@permission_classes([])
@authentication_classes([])
def update_agent(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    update_agent_task.delay(agent.pk)

    return Response(f"updating {agent.hostname}")


@api_view(["DELETE"])
def uninstall_agent(request):
    pk = request.data["pk"]
    agent = get_object_or_404(Agent, pk=pk)
    
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.hostname, 
            timeout=30, 
            func="test.ping"
        )
    except Exception:
        agent.uninstall_pending = True
        agent.save(update_fields=["uninstall_pending"])
        logger.warning(f"{agent.hostname} is offline. It will be removed on next check-in")
        return Response(
            {"error": "Agent offline. It will be removed on next check-in"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = resp.json()
    if not data["return"][0][agent.hostname]:
        agent.uninstall_pending = True
        agent.save(update_fields=["uninstall_pending"])
        return Response(
            {"error": "Agent offline. It will be removed on next check-in"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(f"{agent.hostname} has been marked for removal and will be uninstalled shortly")
    uninstall_agent_task.delay(pk, wait=False)
    agent.uninstall_pending = True
    agent.save(update_fields=["uninstall_pending"])
    return Response("ok")


@api_view(["PATCH"])
def edit_agent(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    agent.client = request.data["client"]
    agent.site = request.data["site"]
    agent.monitoring_type = request.data["montype"]
    agent.description = request.data["desc"]
    agent.overdue_time = request.data["overduetime"]
    agent.ping_check_interval = request.data["pinginterval"]
    agent.overdue_email_alert = request.data["emailalert"]
    agent.overdue_text_alert = request.data["textalert"]
    agent.save(update_fields=[
        "client", "site", "monitoring_type", "description", "ping_check_interval",
        "overdue_time", "overdue_email_alert", "overdue_text_alert"
    ])
    return Response("ok")


@api_view()
def meshcentral_tabs(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    node = agent.mesh_node_id
    terminalurl = f"{settings.MESH_SITE}/?user={settings.MESH_USERNAME}&pass={settings.MESH_PASSWORD}&node={node}&viewmode=12&hide=31"
    fileurl = f"{settings.MESH_SITE}/?user={settings.MESH_USERNAME}&pass={settings.MESH_PASSWORD}&node={node}&viewmode=13&hide=31"
    return Response({
        "hostname": agent.hostname,
        "terminalurl": terminalurl,
        "fileurl": fileurl
    })


@api_view()
def take_control(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    node = agent.mesh_node_id
    url = f"{settings.MESH_SITE}/?user={settings.MESH_USERNAME}&pass={settings.MESH_PASSWORD}&node={node}&viewmode=11&hide=31"
    return Response(url)


@api_view()
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentSerializer(agent).data)

@api_view()
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.hostname,
            timeout=70,
            func="get_eventlog.get_eventlog",
            arg=[logtype, int(days)]
        )
        data = resp.json()
    except Exception:
        return Response({"error": "unable to contact the agent"}, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(data["return"][0][agent.hostname])


@api_view(["POST"])
def power_action(request):
    pk = request.data["pk"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if action == "rebootnow":
        logger.info(f"{agent.hostname} was scheduled for immediate reboot")
        resp = agent.salt_api_cmd(
            hostname=agent.hostname, timeout=30, func="system.reboot", arg=3, kwargs={"in_seconds": True}
        )

    data = resp.json()
    if not data["return"][0][agent.hostname]:
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
            hostname=agent.hostname, timeout=60, func="cmd.run", arg=cmd
        )
        data = resp.json()
    except Exception:
        return Response(
            "unable to contact the agent", status=status.HTTP_400_BAD_REQUEST
        )

    if not data["return"][0][agent.hostname]:
        return Response(
            "unable to contact the agent", status=status.HTTP_400_BAD_REQUEST
        )
    logger.info(f"The command {cmd} was sent on agent {agent.hostname}")
    return Response(data["return"][0][agent.hostname])


@api_view()
def list_agents(request):
    agents = Agent.objects.all()
    return Response(AgentSerializer(agents, many=True).data)


@api_view()
def by_client(request, client):
    agents = Agent.objects.filter(client=client)
    return Response(AgentSerializer(agents, many=True).data)


@api_view()
def by_site(request, client, site):
    agents = Agent.objects.filter(client=client).filter(site=site)
    return Response(AgentSerializer(agents, many=True).data)


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
