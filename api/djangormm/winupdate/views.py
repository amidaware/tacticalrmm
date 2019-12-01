from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from agents.models import Agent
from .serializers import UpdateSerializer

@api_view()
@authentication_classes([])
@permission_classes([])
def get_win_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(UpdateSerializer(agent).data)