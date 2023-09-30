from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from clients.models import Client
from clients.permissions import ClientsPerms
from ..serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, ClientsPerms]
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    http_method_names = ["get", "put"]
