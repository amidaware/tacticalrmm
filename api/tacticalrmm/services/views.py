import asyncio

from agents.models import Agent
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.utils import notify_error

from .permissions import WinSvcsPerms


class GetServices(APIView):
    permission_classes = [IsAuthenticated, WinSvcsPerms]

    def get(self, request, agent_id):
        if getattr(settings, "DEMO", False):
            from tacticalrmm.demo_views import demo_get_services

            return demo_get_services()

        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd(data={"func": "winservices"}, timeout=10))

        if r == "timeout" or r == "natsdown":
            return notify_error("Unable to contact the agent")

        agent.services = r
        agent.save(update_fields=["services"])
        return Response(agent.services)


class GetEditActionService(APIView):
    permission_classes = [IsAuthenticated, WinSvcsPerms]

    # get agent service details
    def get(self, request, agent_id, svcname):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        data = {"func": "winsvcdetail", "payload": {"name": svcname}}
        r = asyncio.run(agent.nats_cmd(data, timeout=10))
        if r == "timeout":
            return notify_error("Unable to contact the agent")

        return Response(r)

    # win service action
    def post(self, request, agent_id, svcname):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data["sv_action"]
        data = {
            "func": "winsvcaction",
            "payload": {
                "name": svcname,
            },
        }
        # response struct from agent: {success: bool, errormsg: string}
        if action == "restart":
            data["payload"]["action"] = "stop"
            r = asyncio.run(agent.nats_cmd(data, timeout=32))
            if r == "timeout" or r == "natsdown":
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
                    return Response("The service was restarted successfully")
        else:
            data["payload"]["action"] = action
            r = asyncio.run(agent.nats_cmd(data, timeout=32))
            if r == "timeout" or r == "natsdown":
                return notify_error("Unable to contact the agent")
            elif not r["success"] and r["errormsg"]:
                return notify_error(r["errormsg"])
            elif r["success"]:
                return Response(
                    f"The service was {'started' if action == 'start' else 'stopped'} successfully"
                )

        return notify_error("Something went wrong")

    # edit win service
    def put(self, request, agent_id, svcname):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        data = {
            "func": "editwinsvc",
            "payload": {
                "name": svcname,
                "startType": request.data["startType"],
            },
        }

        r = asyncio.run(agent.nats_cmd(data, timeout=10))
        # response struct from agent: {success: bool, errormsg: string}
        if r == "timeout" or r == "natsdown":
            return notify_error("Unable to contact the agent")
        elif not r["success"] and r["errormsg"]:
            return notify_error(r["errormsg"])
        elif r["success"]:
            return Response("The service start type was updated successfully")

        return notify_error("Something went wrong")
