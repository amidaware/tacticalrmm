from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Policy

from .serializers import PolicySerializer

class GetAddPolicies(APIView):

    def get(self, request):

        policies = Policy.objects.all()

        return Response(PolicySerializer(policies, many=True).data)

    def post(self, request):
        name = request.data["name"].strip()
        desc = request.data["desc"].strip()

        if Policy.objects.filter(name=name):
            content = {"error": f"Policy {name} already exists"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        try:
            Policy(name=name, desc=desc).save()
        except DataError:
            content = {"error": "Policy name too long (max 255 chars)"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("ok")

class GetAddDeletePolicy(APIView):     

    def get(self, request, pk):

        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicySerializer(policy).data)

    def put(self, request, pk):

        policy = get_object_or_404(Policy, pk=pk)

        policy.name = request.data["name"]
        policy.desc = request.data["desc"]
        policy.active = request.data["active"]

        try:
            policy.save(update_fields=["name", "desc", "active"])
        except DataError:
            content = {"error": "Policy name too long (max 255 chars)"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        #Client, Site, Agent Many to Many Logic Here

        return Response("ok")

    def delete(self, request, pk):

        policy = Policy.objects.get(pk=pk)
        policy.delete()

        return Response("ok")
