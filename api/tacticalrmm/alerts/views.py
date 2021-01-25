from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime as dt
from django.utils import timezone as djangotime

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Alert, AlertTemplate

from .serializers import AlertSerializer, AlertTemplateSerializer


class GetAddAlerts(APIView):
    def patch(self, request):

        # top 10 alerts for dashboard icon
        if "top" in request.data.keys():
            alerts = Alert.objects.filter(resolved=False, snooze_until=None).order_by(
                "alert_time"
            )[: int(request.data["top"])]
            count = Alert.objects.filter(resolved=False).count()
            return Response(
                {
                    "alerts_count": count,
                    "alerts": AlertSerializer(alerts, many=True).data,
                }
            )

        elif any(
            key
            in [
                "timeFilter",
                "clientFilter",
                "severityFilter",
                "resolvedFilter",
                "snoozedFilter",
            ]
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
                Alert.objects.filter(clientFilter)
                .filter(severityFilter)
                .filter(resolvedFilter)
                .filter(snoozedFilter)
                .filter(timeFilter)
            )
            return Response(AlertSerializer(alerts, many=True).data)

        else:
            alerts = Alert.objects.all()
            return Response(AlertSerializer(alerts, many=True).data)

    def post(self, request):
        serializer = AlertSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeleteAlert(APIView):
    def get(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)

        return Response(AlertSerializer(alert).data)

    def put(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)

        serializer = AlertSerializer(instance=alert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        Alert.objects.get(pk=pk).delete()

        return Response("ok")


class GetAddAlertTemplates(APIView):
    def get(self, request):
        alert_templates = AlertTemplate.objects.all()

        return Response(AlertTemplateSerializer(alert_templates, many=True).data)

    def post(self, request):
        serializer = AlertTemplateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeleteAlertTemplate(APIView):
    def get(self, request, pk):
        alert = get_object_or_404(AlertTemplate, pk=pk)

        return Response(AlertSerializer(alert).data)

    def put(self, request, pk):
        alert_template = get_object_or_404(AlertTemplate, pk=pk)

        serializer = AlertTemplateSerializer(
            instance=alert_template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(AlertTemplate, pk=pk).delete()

        return Response("ok")
