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
from checks.serializers import CheckSerializer
from agents.serializers import AgentHostnameSerializer

from .serializers import (
    PolicySerializer,
    PolicyTableSerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
    AutoTaskPolicySerializer,
)

from .tasks import generate_agent_checks_from_policies_task


class GetAddPolicies(APIView):
    def get(self, request):
        policies = Policy.objects.all()

        return Response(PolicyTableSerializer(policies, many=True).data)

    def post(self, request):
        serializer = PolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeletePolicy(APIView):
    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        return Response(PolicySerializer(policy).data)

    def put(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        old_active = policy.active
        old_enforced = policy.enforced

        serializer = PolicySerializer(instance=policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved_policy = serializer.save()

        # Generate agent checks only if active and enforced were changed
        if saved_policy.active != old_active or saved_policy.enforced != old_enforced:
            generate_agent_checks_from_policies_task.delay(policypk=policy.pk)

        return Response("ok")

    def delete(self, request, pk):
        policy = Policy.objects.get(pk=pk)

        # delete all managed policy checks off of agents
        parent_check_pks = policy.policychecks.only("pk")
        if parent_check_pks:
            Check.objects.filter(parent_check__in=parent_check_pks).delete()

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
            policy = get_object_or_404(Policy, pk=request.data["policy"])
            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)
                
                # Check and see if policy changed and regenerate policies
                if not client.policy or client.policy and client.policy.pk != policy.pk:
                    client.policy = policy
                    client.save()
                    generate_agent_checks_from_policies_task.delay(policypk=policy.pk)

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)

                # Check and see if policy changed and regenerate policies
                if not site.policy or site.policy and site.policy.pk != policy.pk:
                    site.policy = policy
                    site.save()
                    generate_agent_checks_from_policies_task.delay(policypk=policy.pk)

            if related_type == "agent":
                agent = get_object_or_404(Agent, pk=pk)

                # Check and see if policy changed and regenerate policies
                if not agent.policy or agent.policy and agent.policy.pk != policy.pk:
                    agent.policy=policy
                    agent.save()
                    agent.generate_checks_from_policies()

        # If policy was cleared
        else:
            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)

                # Check if policy is not none and update it to None
                if client.policy:

                    # Get old policy pk to regenerate the checks
                    old_pk = client.pk
                    client.policy=None
                    client.save()
                    generate_agent_checks_from_policies_task.delay(policypk=old_pk)

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)

                # Check if policy is not none and update it to None
                if site.policy:

                    # Get old policy pk to regenerate the checks
                    old_pk = site.pk
                    site.policy=None
                    site.save()
                    generate_agent_checks_from_policies_task.delay(policypk=old_pk)

            if related_type == "agent":
                agent = get_object_or_404(Agent, pk=pk)

                if agent.policy:
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
