from datetime import datetime as dt

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.helpers import notify_error

from .models import Alert, AlertTemplate
from .permissions import AlertPerms, AlertTemplatePerms
from .serializers import (
    AlertSerializer,
    AlertTemplateRelationSerializer,
    AlertTemplateSerializer,
)
from .tasks import cache_agents_alert_template


class GetAddAlerts(APIView):
    permission_classes = [IsAuthenticated, AlertPerms]

    def patch(self, request):
        # top 10 alerts for dashboard icon
        if "top" in request.data.keys():
            alerts = (
                Alert.objects.filter_by_role(request.user)  # type: ignore
                .filter(resolved=False, snoozed=False, hidden=False)
                .order_by("alert_time")[: int(request.data["top"])]
            )
            count = (
                Alert.objects.filter_by_role(request.user)  # type: ignore
                .filter(resolved=False, snoozed=False, hidden=False)
                .count()
            )
            return Response(
                {
                    "alerts_count": count,
                    "alerts": AlertSerializer(alerts, many=True).data,
                }
            )

        elif any(
            key
            in (
                "timeFilter",
                "clientFilter",
                "severityFilter",
                "resolvedFilter",
                "snoozedFilter",
            )
            for key in request.data.keys()
        ):
            clientFilter = Q()
            severityFilter = Q()
            timeFilter = Q()
            resolvedFilter = Q()
            snoozedFilter = Q()

            if (
                "snoozedFilter" in request.data.keys()
                and not request.data["snoozedFilter"]
            ):
                snoozedFilter = Q(snoozed=request.data["snoozedFilter"])

            if (
                "resolvedFilter" in request.data.keys()
                and not request.data["resolvedFilter"]
            ):
                resolvedFilter = Q(resolved=request.data["resolvedFilter"])

            if "clientFilter" in request.data.keys():
                from agents.models import Agent
                from clients.models import Client

                clients = Client.objects.filter(
                    pk__in=request.data["clientFilter"]
                ).values_list("id")
                agents = Agent.objects.filter(site__client_id__in=clients).values_list(
                    "id"
                )

                clientFilter = Q(agent__in=agents)

            if "severityFilter" in request.data.keys():
                severityFilter = Q(severity__in=request.data["severityFilter"])

            if "timeFilter" in request.data.keys():
                timeFilter = Q(
                    alert_time__lte=djangotime.make_aware(dt.today()),
                    alert_time__gt=djangotime.make_aware(dt.today())
                    - djangotime.timedelta(days=int(request.data["timeFilter"])),
                )

            alerts = (
                Alert.objects.filter_by_role(request.user)  # type: ignore
                .filter(clientFilter)
                .filter(severityFilter)
                .filter(resolvedFilter)
                .filter(snoozedFilter)
                .filter(timeFilter)
            )
            return Response(AlertSerializer(alerts, many=True).data)

        else:
            alerts = Alert.objects.filter_by_role(request.user)  # type: ignore
            return Response(AlertSerializer(alerts, many=True).data)

    def post(self, request):
        serializer = AlertSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeleteAlert(APIView):
    permission_classes = [IsAuthenticated, AlertPerms]

    def get(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        return Response(AlertSerializer(alert).data)

    def put(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)

        data = request.data

        if "type" in data.keys():
            if data["type"] == "resolve":
                data = {
                    "resolved": True,
                    "resolved_on": djangotime.now(),
                    "snoozed": False,
                }

                # unable to set snooze_until to none in serialzier
                alert.snooze_until = None
                alert.save()
            elif data["type"] == "snooze":
                if "snooze_days" in data.keys():
                    data = {
                        "snoozed": True,
                        "snooze_until": djangotime.now()
                        + djangotime.timedelta(days=int(data["snooze_days"])),
                    }
                else:
                    return notify_error(
                        "Missing 'snoozed_days' when trying to snooze alert"
                    )
            elif data["type"] == "unsnooze":
                data = {"snoozed": False}

                # unable to set snooze_until to none in serialzier
                alert.snooze_until = None
                alert.save()
            else:
                return notify_error("There was an error in the request data")

        serializer = AlertSerializer(instance=alert, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        Alert.objects.get(pk=pk).delete()

        return Response("ok")


class BulkAlerts(APIView):
    permission_classes = [IsAuthenticated, AlertPerms]

    def post(self, request):
        if request.data["bulk_action"] == "resolve":
            Alert.objects.filter(id__in=request.data["alerts"]).update(
                resolved=True,
                resolved_on=djangotime.now(),
                snoozed=False,
                snooze_until=None,
            )
            return Response("ok")
        elif request.data["bulk_action"] == "snooze":
            if "snooze_days" in request.data.keys():
                Alert.objects.filter(id__in=request.data["alerts"]).update(
                    snoozed=True,
                    snooze_until=djangotime.now()
                    + djangotime.timedelta(days=int(request.data["snooze_days"])),
                )
                return Response("ok")

        return notify_error("The request was invalid")


class GetAddAlertTemplates(APIView):
    permission_classes = [IsAuthenticated, AlertTemplatePerms]

    def get(self, request):
        alert_templates = AlertTemplate.objects.all()
        return Response(AlertTemplateSerializer(alert_templates, many=True).data)

    def post(self, request):
        serializer = AlertTemplateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # cache alert_template value on agents
        cache_agents_alert_template.delay()

        return Response("ok")


class GetUpdateDeleteAlertTemplate(APIView):
    permission_classes = [IsAuthenticated, AlertTemplatePerms]

    def get(self, request, pk):
        alert_template = get_object_or_404(AlertTemplate, pk=pk)

        return Response(AlertTemplateSerializer(alert_template).data)

    def put(self, request, pk):
        alert_template = get_object_or_404(AlertTemplate, pk=pk)

        serializer = AlertTemplateSerializer(
            instance=alert_template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # cache alert_template value on agents
        cache_agents_alert_template.delay()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(AlertTemplate, pk=pk).delete()

        # cache alert_template value on agents
        cache_agents_alert_template.delay()

        return Response("ok")


class RelatedAlertTemplate(APIView):
    permission_classes = [IsAuthenticated, AlertTemplatePerms]

    def get(self, request, pk):
        alert_template = get_object_or_404(AlertTemplate, pk=pk)
        return Response(AlertTemplateRelationSerializer(alert_template).data)
