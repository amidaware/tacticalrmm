import asyncio
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
    r = asyncio.run(agent.nats_cmd(data={"func": "winservices"}, timeout=10))

    if r == "timeout":
        return notify_error("Unable to contact the agent")

    agent.services = r
    agent.save(update_fields=["services"])
    return Response(ServicesSerializer(agent).data)


@api_view(["POST"])
def service_action(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    action = request.data["sv_action"]
    data = {
        "func": "winsvcaction",
        "payload": {
            "name": request.data["sv_name"],
        },
    }
    # response struct from agent: {success: bool, errormsg: string}
    if action == "restart":
        data["payload"]["action"] = "stop"
        r = asyncio.run(agent.nats_cmd(data, timeout=32))
        if r == "timeout":
            return notify_error("Unable to contact the agent")
        elif not r["success"] and r["errormsg"]:
            return notify_error(r["errormsg"])
        elif r["success"]:
            data["payload"]["action"] = "start"
            r = asyncio.run(agent.nats_cmd(data, timeout=32))
            if r == "timeout":
                return notify_error("Unable to contact the agent")
            elif not r["success"] and r["errormsg"]:
                return notify_error(r["errormsg"])
            elif r["success"]:
                return Response("ok")
    else:
        data["payload"]["action"] = action
        r = asyncio.run(agent.nats_cmd(data, timeout=32))
        if r == "timeout":
            return notify_error("Unable to contact the agent")
        elif not r["success"] and r["errormsg"]:
            return notify_error(r["errormsg"])
        elif r["success"]:
            return Response("ok")

    return notify_error("Something went wrong")


@api_view()
def service_detail(request, pk, svcname):
    agent = get_object_or_404(Agent, pk=pk)
    data = {"func": "winsvcdetail", "payload": {"name": svcname}}
    r = asyncio.run(agent.nats_cmd(data, timeout=10))
    if r == "timeout":
        return notify_error("Unable to contact the agent")

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
