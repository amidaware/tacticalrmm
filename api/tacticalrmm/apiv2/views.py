from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from checks.models import Check

from checks.serializers import CheckRunnerGetSerializerV2


class CheckRunner(APIView):
    """
    For the windows python agent
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agentid):
        agent = get_object_or_404(Agent, agent_id=agentid)
        agent.last_seen = djangotime.now()
        agent.save(update_fields=["last_seen"])
        checks = Check.objects.filter(agent__pk=agent.pk, overriden_by_policy=False)

        ret = {
            "agent": agent.pk,
            "check_interval": agent.check_interval,
            "checks": CheckRunnerGetSerializerV2(checks, many=True).data,
        }
        return Response(ret)

    def patch(self, request):
        check = get_object_or_404(Check, pk=request.data["id"])
        check.last_run = djangotime.now()
        check.save(update_fields=["last_run"])
        status = check.handle_checkv2(request.data)
        return Response(status)
