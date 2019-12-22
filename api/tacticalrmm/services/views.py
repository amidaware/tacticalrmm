from loguru import logger

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from django.conf import settings
from django.shortcuts import get_object_or_404

from agents.models import Agent
from .serializers import ServicesSerializer

logger.configure(**settings.LOG_CONFIG)

@api_view()
def get_services(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(ServicesSerializer(agent).data)

@api_view()
def get_refreshed_services(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    try:
        resp = agent.salt_api_cmd(
            hostname=agent.hostname,
            timeout=30,
            func="get_services.get_services"
        )
        data = resp.json()
    except Exception:
        error = {"error": "unable to contact the agent"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
        
    if not data["return"][0][agent.hostname]:
        error = {"error": "unable to contact the agent"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
    agent.services = data["return"][0][agent.hostname]
    agent.save(update_fields=["services"])
    return Response(ServicesSerializer(agent).data)

@api_view(["POST"])
def service_action(request):
    data = request.data
    pk = data["pk"]
    service_name = data["sv_name"]
    service_action = data["sv_action"]
    agent = get_object_or_404(Agent, pk=pk)
    resp = agent.salt_api_cmd(
        hostname = agent.hostname,
        timeout = 60,
        func = f"service.{service_action}",
        arg = service_name,
    )
    data = resp.json()
    if not data["return"][0][agent.hostname]:
        error = {"error": "unable to contact the agent"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"The {service_name} service on {agent.hostname} was sent the {service_action} command")
    return Response("ok")

@api_view()
def service_detail(request, pk, svcname):
    agent = get_object_or_404(Agent, pk=pk)
    resp = agent.salt_api_cmd(
        hostname = agent.hostname,
        timeout = 60,
        func = "service.info",
        arg = svcname,
    )
    data = resp.json()
    if not data["return"][0][agent.hostname]:
        error = {"error": "unable to contact the agent"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(data["return"][0][agent.hostname])

@api_view(["POST"])
def edit_service(request):
    data = request.data
    pk = data["pk"]
    service_name = data["sv_name"]
    edit_action = data["edit_action"]

    agent = get_object_or_404(Agent, pk=pk)

    if edit_action == "autodelay":
        kwargs = {"start_type": "auto", "start_delayed": True}
    elif edit_action == "auto":
        kwargs = {"start_type": "auto", "start_delayed": False}
    else:
        kwargs = {"start_type": edit_action}
    
    try:
        resp = agent.salt_api_cmd(
            hostname = agent.hostname,
            timeout = 60,
            func = "service.modify",
            arg = service_name,
            kwargs = kwargs,
        )
    except Exception as e:
        return Response(
            {"error": "Unable to contact the agent"}, status=status.HTTP_400_BAD_REQUEST
        )
    else:
        logger.info(f"The {service_name} on {agent.hostname} was modified: {kwargs}")
        return Response("ok")
