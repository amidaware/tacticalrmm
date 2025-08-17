from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from clients.models import Site
from clients.permissions import SitesPerms
from beta.v1.pagination import StandardResultsSetPagination
from ..serializers import SiteSerializer


class SiteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, SitesPerms]
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "put"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id"]
    ordering = ["id"]
