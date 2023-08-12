import asyncio
from typing import Dict, Tuple, Union

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from tacticalrmm.helpers import notify_error

from .permissions import WinSvcsPerms


def process_nats_response(data: Union[str, Dict]) -> Tuple[bool, bool, str]:
    natserror = isinstance(data, str)
    success = (
        data["success"]
        if isinstance(data, dict) and isinstance(data["success"], bool)
        else False
    )
    errormsg = (
        data["errormsg"]
        if isinstance(data, dict) and isinstance(data["errormsg"], str)
        else "timeout"
    )

    return success, natserror, errormsg


class GetServices(APIView):
    permission_classes = [IsAuthenticated, WinSvcsPerms]

    def get(self, request, agent_id):
        if getattr(settings, "DEMO", False):
            from tacticalrmm.demo_views import demo_get_services

            return demo_get_services()

        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd(data={"func": "winservices"}, timeout=10))

        if r in ("timeout", "natsdown"):
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
        if agent.is_posix:
            return notify_error("Please use 'Recover Connection' instead.")
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
            success, natserror, errormsg = process_nats_response(r)

            if errormsg == "timeout" or natserror:
                return notify_error("Unable to contact the agent")
            elif not success and errormsg:
                return notify_error(errormsg)
            elif success:
                data["payload"]["action"] = "start"
                r = asyncio.run(agent.nats_cmd(data, timeout=32))
                success, natserror, errormsg = process_nats_response(r)

                if errormsg == "timeout" or natserror:
                    return notify_error("Unable to contact the agent")
                elif not success and errormsg:
                    return notify_error(errormsg)
                elif success:
                    return Response("The service was restarted successfully")
        else:
            data["payload"]["action"] = action
            r = asyncio.run(agent.nats_cmd(data, timeout=32))
            success, natserror, errormsg = process_nats_response(r)

            if errormsg == "timeout" or natserror:
                return notify_error("Unable to contact the agent")
            elif not success and errormsg:
                return notify_error(errormsg)
            elif success:
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
        success, natserror, errormsg = process_nats_response(r)
        # response struct from agent: {success: bool, errormsg: string}
        if r == "timeout" or natserror:
            return notify_error("Unable to contact the agent")
        elif not success and errormsg:
            return notify_error(errormsg)
        elif success:
            return Response("The service start type was updated successfully")

        return notify_error("Something went wrong")
