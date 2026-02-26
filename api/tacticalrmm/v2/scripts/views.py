from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scripts.models import Script
from scripts.permissions import ScriptsPerms
from scripts.serializers import ScriptTableSerializer

from .filter import ScriptFilter

FILTERABLE_FIELDS = {"category", "shell", "script_type", "supported_platforms"}


class ScriptCursorPagination(CursorPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000
    ordering = ("category", "id")

    def get_next_link(self):
        link = super().get_next_link()
        if link is None:
            return None
        from urllib.parse import urlparse, parse_qs
        cursor = parse_qs(urlparse(link).query).get("cursor", [None])[0]
        return cursor

    def get_previous_link(self):
        link = super().get_previous_link()
        if link is None:
            return None
        from urllib.parse import urlparse, parse_qs
        cursor = parse_qs(urlparse(link).query).get("cursor", [None])[0]
        return cursor


class ScriptFiltersView(APIView):
    permission_classes = [IsAuthenticated, ScriptsPerms]

    def get(self, request):
        requested = request.query_params.get("fields", "")
        fields = {f.strip() for f in requested.split(",") if f.strip()} & FILTERABLE_FIELDS

        if not fields:
            return Response(
                {"fields": f"This field is required. Allowed values: {sorted(FILTERABLE_FIELDS)}"},
                status=400,
            )

        # apply same filters as list endpoint
        queryset = ScriptFilter(request.query_params, queryset=Script.objects.all()).qs

        result = {}
        for field in fields:
            if field == "supported_platforms":
                from django.db.models.expressions import RawSQL
                values = (
                    queryset.annotate(
                        platform=RawSQL("unnest(supported_platforms)", [])
                    )
                    .values_list("platform", flat=True)
                    .distinct()
                    .order_by("platform")
                )
            else:
                values = (
                    queryset.exclude(**{f"{field}__isnull": True})
                    .exclude(**{f"{field}__exact": ""})
                    .order_by(field)
                    .values_list(field, flat=True)
                    .distinct()
                )
            result[field] = list(values)

        return Response(result)


class ScriptViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, ScriptsPerms]
    queryset = Script.objects.all()
    serializer_class = ScriptTableSerializer
    pagination_class = ScriptCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ScriptFilter
    search_fields = ["name"]
