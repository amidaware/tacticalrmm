

from django.db import DataError
from django.shortcuts import get_object_or_404


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from .models import Policy
from agents.models import Agent
from checks.models import Script
from clients.models import Client, Site

from clients.serializers import (
    ClientSerializer,
    TreeSerializer
)

from agents.serializers import AgentHostnameSerializer

from .serializers import (
    PolicySerializer,
    PolicyRelationSerializer,
    AutoTaskPolicySerializer,
)

class GetAddPolicies(APIView):
    def get(self, request):

        policies = Policy.objects.all()

        return Response(PolicyRelationSerializer(policies, many=True).data)

    def post(self, request):
        name = request.data["name"].strip()
        desc = request.data["desc"].strip()
        active = request.data["active"]

        if Policy.objects.filter(name=name):
            content = {"error": f"Policy {name} already exists"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        try:
            policy = Policy.objects.create(name=name, desc=desc, active=active)
        except DataError:
            content = {"error": "Policy name too long (max 255 chars)"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # Add Clients, Sites to Policy
        if len(request.data["clients"]) > 0:
            policy.clients.set(request.data["clients"])

        if len(request.data["sites"]) > 0:
            policy.sites.set(request.data["sites"])

        return Response("ok")


class GetUpdateDeletePolicy(APIView):
    def get(self, request, pk):

        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicyRelationSerializer(policy).data)

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

        # Update Clients, Sites to Policy
        if len(request.data["clients"]) > 0:
            policy.clients.set(request.data["clients"])
        else:
            policy.clients.clear()

        if len(request.data["sites"]) > 0:
            policy.sites.set(request.data["sites"])
        else:
            policy.sites.clear()

        return Response("ok")

    def delete(self, request, pk):

        policy = Policy.objects.get(pk=pk)
        policy.delete()

        return Response("ok")


class PolicyAutoTask(APIView):
    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)
        return Response(AutoTaskPolicySerializer(policy).data)

class RunPolicyTask(APIView):
    def get(self, request, pk):

        # TODO: Run tasks for all Agents under policy
        return Response("ok")


class OverviewPolicy(APIView):
    def get(self, request):

        clients = Client.objects.all()
        response = {}

        for client in clients:

            client_sites = {}
            client_sites["sites"] = {}

            policies = Policy.objects.filter(clients__id=client.id)
            client_sites["policies"] = list(PolicySerializer(policies, many=True).data)

            sites = Site.objects.filter(client=client)

            for site in sites:

                client_sites["sites"][site.site] = {}

                policies = Policy.objects.filter(sites__id=site.id)

                client_sites["sites"][site.site]["policies"] = list(
                    PolicySerializer(policies, many=True).data
                )

            response[client.client] = client_sites


        return Response(response)

class GetRelated(APIView):
    def get(self, request, pk):

        response = {}

        policy = Policy.objects.filter(pk=pk).prefetch_related("clients", "sites").first()

        response["clients"] = ClientSerializer(policy.clients.all(), many=True).data
       
        filtered_sites = list()

        for client in policy.clients.all():
            for site in client.sites.all():
                if site not in policy.sites.all():
                    filtered_sites.append(site)

        response["sites"] = TreeSerializer(filtered_sites + list(policy.sites.all()), many=True).data

        response["agents"] = AgentHostnameSerializer(policy.related_agents(), many=True).data

        return Response(response)