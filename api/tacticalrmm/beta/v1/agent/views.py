from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer

from agents.models import Agent
from agents.permissions import AgentPerms
from beta.v1.agent.filter import AgentFilter
from beta.v1.pagination import StandardResultsSetPagination
from ..serializers import DetailAgentSerializer, ListAgentSerializer


class AgentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, AgentPerms]
    queryset = Agent.objects.all()
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "put"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AgentFilter
    search_fields = ["hostname", "services"]
    ordering_fields = ["id"]
    ordering = ["id"]

    def check_permissions(self, request: Request) -> None:
        if "agent_id" in request.query_params:
            self.kwargs["agent_id"] = request.query_params["agent_id"]
        super().check_permissions(request)

    def get_permissions(self):
        if self.request.method == "POST":
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.kwargs:
            if self.kwargs["pk"]:
                return DetailAgentSerializer
        return ListAgentSerializer
