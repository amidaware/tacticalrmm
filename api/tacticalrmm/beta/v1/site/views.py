from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from clients.models import Site
from clients.permissions import SitesPerms
from tacticalrmm.pagination import StandardPagination

from ..serializers import SiteSerializer


class SiteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, SitesPerms]
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    pagination_class = StandardPagination
    http_method_names = ["get", "put"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id"]
    ordering = ["id"]
