from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from agents.models import Agent
from .models import WinUpdate
from .serializers import UpdateSerializer, WinUpdateSerializer, ApprovedUpdateSerializer
from .tasks import check_for_updates_task

@api_view()
@authentication_classes([])
@permission_classes([])
def get_win_updates(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(UpdateSerializer(agent).data)

@api_view()
def run_update_scan(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    check_for_updates_task.delay(agent.pk)
    return Response("ok")

@api_view(["PATCH"])
def edit_policy(request):
    patch = get_object_or_404(WinUpdate, pk=request.data["pk"])
    patch.action = request.data["policy"]
    patch.save(update_fields=["action"])
    return Response("ok")


@api_view()
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def win_updater(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agentid"])
    patches = WinUpdate.objects.filter(agent=agent).exclude(installed=True).filter(action="approve")
    if patches:
        return Response(ApprovedUpdateSerializer(patches, many=True).data)
        
    return Response("nopatches")

@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def results(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agentid"])
    kb = request.data["kb"]
    results = request.data["results"]
    update = WinUpdate.objects.filter(agent=agent).get(kb=kb)

    if results == "error" or results == "failed":
        update.result = results
        update.save(update_fields=["result"])

    elif results == "success" or results == "alreadyinstalled":
        update.result = "success"
        update.action = "nothing"
        update.downloaded = True
        update.installed = True
        update.save(update_fields=["result", "action", "downloaded", "installed"])


    return Response("ok")
