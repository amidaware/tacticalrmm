from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from loguru import logger
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from tacticalrmm.utils import notify_error

from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)


@api_view()
@permission_classes([])
@authentication_classes([])
def nats_info(request):
    return Response({"user": "tacticalrmm", "password": settings.SECRET_KEY})


class NatsAgents(APIView):
    authentication_classes = []  # type: ignore
    permission_classes = []  # type: ignore

    def get(self, request, stat: str):
        if stat not in ["online", "offline"]:
            return notify_error("invalid request")

        ret: list[str] = []
        agents = Agent.objects.only(
            "pk", "agent_id", "version", "last_seen", "overdue_time", "offline_time"
        )
        if stat == "online":
            ret = [i.agent_id for i in agents if i.status == "online"]
        else:
            ret = [i.agent_id for i in agents if i.status != "online"]

        return Response({"agent_ids": ret})


class LogCrash(APIView):
    authentication_classes = []  # type: ignore
    permission_classes = []  # type: ignore

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agentid"])
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["last_seen"])

        if hasattr(settings, "DEBUGTEST") and settings.DEBUGTEST:
            logger.info(
                f"Detected crashed tacticalagent service on {agent.hostname} v{agent.version}, attempting recovery"
            )

        return Response("ok")
