from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Alert

from .serializers import AlertSerializer


class GetAddAlerts(APIView):
    def get(self, request):
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
