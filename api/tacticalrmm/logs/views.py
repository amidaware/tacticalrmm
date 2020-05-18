from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from .models import PendingAction
from .serializers import PendingActionSerializer
from .tasks import cancel_pending_action_task


@api_view()
def agent_pending_actions(request, pk):
    action = PendingAction.objects.filter(agent__pk=pk)
    return Response(PendingActionSerializer(action, many=True).data)


@api_view()
def all_pending_actions(request):
    actions = PendingAction.objects.all()
    return Response(PendingActionSerializer(actions, many=True).data)


@api_view(["DELETE"])
def cancel_pending_action(request):
    action = get_object_or_404(PendingAction, pk=request.data["pk"])
    data = PendingActionSerializer(action).data
    cancel_pending_action_task.delay(data)
    action.delete()
    return Response(
        f"{action.agent.hostname}: {action.description} will be cancelled shortly"
    )
