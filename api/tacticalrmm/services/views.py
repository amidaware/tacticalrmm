from loguru import logger

from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.conf import settings
from django.shortcuts import get_object_or_404

from agents.models import Agent
from checks.models import Check

from .serializers import ServicesSerializer

from tacticalrmm.utils import notify_error

logger.configure(**settings.LOG_CONFIG)


@api_view()
def get_services(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(ServicesSerializer(agent).data)


@api_view()
def default_services(request):
    return Response(Check.load_default_services())


@api_view()
def get_refreshed_services(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=15, func="win_agent.get_services")

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    agent.services = r
    agent.save(update_fields=["services"])
    return Response(ServicesSerializer(agent).data)


@api_view(["POST"])
def service_action(request):
    data = request.data
    pk = data["pk"]
    service_name = data["sv_name"]
    service_action = data["sv_action"]
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(
        timeout=45,
        func=f"service.{service_action}",
        arg=service_name,
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    return Response("ok")


@api_view()
def service_detail(request, pk, svcname):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=20, func="service.info", arg=svcname)

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    return Response(r)


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

    r = agent.salt_api_cmd(
        timeout=20,
        func="service.modify",
        arg=service_name,
        kwargs=kwargs,
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    return Response("ok")
