from django.db import DataError
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Policy
from agents.models import Agent
from scripts.models import Script
from clients.models import Client, Site
from checks.models import Check

from clients.serializers import ClientSerializer, TreeSerializer

from agents.serializers import AgentHostnameSerializer

from .serializers import (
    PolicySerializer,
    PolicyTableSerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
    AutoTaskPolicySerializer,
)

from checks.serializers import CheckSerializer


class GetAddPolicies(APIView):
    def get(self, request):

        policies = Policy.objects.all()

        return Response(PolicyTableSerializer(policies, many=True).data)

    def post(self, request):
        name = request.data["name"].strip()
        desc = request.data["desc"].strip()
        active = request.data["active"]
        enforced = active = request.data["enforced"]

        if Policy.objects.filter(name=name):
            content = {"error": f"Policy {name} already exists"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        try:
            policy = Policy.objects.create(
                name=name, desc=desc, active=active, enforced=enforced
            )
        except DataError:
            content = {"error": "Policy name too long (max 255 chars)"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        return Response("ok")


class GetUpdateDeletePolicy(APIView):
    def get(self, request, pk):

        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicySerializer(policy).data)

    def put(self, request, pk):

        policy = get_object_or_404(Policy, pk=pk)

        policy.name = request.data["name"]
        policy.desc = request.data["desc"]
        policy.active = request.data["active"]
        policy.enforced = request.data["enforced"]

        try:
            policy.save(update_fields=["name", "desc", "active", "enforced"])
        except DataError:
            content = {"error": "Policy name too long (max 255 chars)"}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        return Response("ok")

    def delete(self, request, pk):
        policy = Policy.objects.get(pk=pk)
        policy.delete()

        return Response("ok")


class PolicyAutoTask(APIView):
    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)
        return Response(AutoTaskPolicySerializer(policy).data)

    def patch(self, request, policy, task):

        # TODO pull agents and status for policy task
        return Response(list())

    def put(self, request, pk):
        return Response("ok")


class PolicyCheck(APIView):
    def get(self, request, pk):
        checks = Check.objects.filter(policy__pk=pk, agent=None)
        return Response(CheckSerializer(checks, many=True).data)

    def patch(self, request, check):

        checks = Check.objects.filter(parent_check=check)
        return Response(PolicyCheckStatusSerializer(checks, many=True).data)

    def put(self, request):

        # TODO run policy check manually for all agents
        return Response(list())


class OverviewPolicy(APIView):
    def get(self, request):

        clients = Client.objects.all()
        return Response(PolicyOverviewSerializer(clients, many=True).data)


class GetRelated(APIView):
    def get(self, request, pk):

        response = {}

        policy = (
            Policy.objects.filter(pk=pk).prefetch_related("clients", "sites").first()
        )

        response["clients"] = ClientSerializer(policy.clients.all(), many=True).data

        filtered_sites = list()

        for client in policy.clients.all():
            for site in client.sites.all():
                if site not in policy.sites.all():
                    filtered_sites.append(site)

        response["sites"] = TreeSerializer(
            filtered_sites + list(policy.sites.all()), many=True
        ).data

        response["agents"] = AgentHostnameSerializer(
            policy.related_agents(), many=True
        ).data

        return Response(response)

    def post(self, request):
        # Update Agents, Clients, Sites to Policy

        related_type = request.data["type"]
        pk = request.data["pk"]

        if request.data["policy"] != 0:
            policy = Policy.objects.get(pk=request.data["policy"])
            if related_type == "client":
                Client.objects.filter(pk=pk).update(policy=policy)

            if related_type == "site":
                Site.objects.filter(pk=pk).update(policy=policy)

            if related_type == "agent":
                agent = Agent.objects.get(pk=pk)
                agent.policy=policy
                agent.save()
                agent.generate_checks_from_policies()

        else:
            if related_type == "client":
                Client.objects.filter(pk=pk).update(policy=None)

            if related_type == "site":
                Site.objects.filter(pk=pk).update(policy=None)

            if related_type == "agent":
                agent = Agent.objects.get(pk=pk)
                agent.policy=None
                agent.save()
                agent.generate_checks_from_policies()

        return Response("ok")

    def patch(self, request):
        related_type = request.data["type"]
        pk = request.data["pk"]

        if related_type == "agent":
            policy = Policy.objects.filter(agents__pk=pk).first()
            return Response(PolicySerializer(policy).data)

        if related_type == "site":
            policy = Policy.objects.filter(sites__pk=pk).first()
            return Response(PolicySerializer(policy).data)

        if related_type == "client":
            policy = Policy.objects.filter(clients__pk=pk).first()
            return Response(PolicySerializer(policy).data)

        content = {"error": "Data was submitted incorrectly"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)
