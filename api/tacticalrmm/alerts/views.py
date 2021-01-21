from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Alert, AlertTemplate

from .serializers import AlertSerializer, AlertTemplateSerializer


class GetAddAlerts(APIView):
    def get(self, request):
        alerts = Alert.objects.all()

        # Add time and severity filters

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
