from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Policy
from agents.models import Agent
from clients.models import Client, Site
from checks.models import Check
from autotasks.models import AutomatedTask
from winupdate.models import WinUpdatePolicy

from clients.serializers import ClientSerializer, SiteSerializer
from agents.serializers import AgentHostnameSerializer
from winupdate.serializers import WinUpdatePolicySerializer

from .serializers import (
    PolicySerializer,
    PolicyTableSerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
    PolicyCheckSerializer,
    PolicyTaskStatusSerializer,
    AutoTaskPolicySerializer,
    RelatedClientPolicySerializer,
    RelatedSitePolicySerializer,
    RelatedAgentPolicySerializer,
)

from .tasks import (
    generate_agent_checks_from_policies_task,
    generate_agent_checks_by_location_task,
    generate_agent_tasks_from_policies_task,
    run_win_policy_autotask_task,
)


class GetAddPolicies(APIView):
    def get(self, request):
        policies = Policy.objects.all()

        return Response(PolicyTableSerializer(policies, many=True).data)

    def post(self, request):
        serializer = PolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()

        # copy checks and tasks from specified policy
        if "copyId" in request.data:
            copyPolicy = Policy.objects.get(pk=request.data["copyId"])

            checks = copyPolicy.policychecks.all()
            for check in checks:
                check.create_policy_check(policy=policy)

            tasks = copyPolicy.autotasks.all()

            for task in tasks:
                task.create_policy_task(policy=policy)

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
            generate_agent_checks_from_policies_task.delay(
                policypk=policy.pk,
                clear=(not saved_policy.active or not saved_policy.enforced),
                create_tasks=(saved_policy.active != old_active),
            )

        return Response("ok")

    def delete(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)

        # delete all managed policy checks off of agents
        generate_agent_checks_from_policies_task.delay(policypk=policy.pk, clear=True)
        generate_agent_tasks_from_policies_task.delay(policypk=policy.pk, clear=True)
        policy.delete()

        return Response("ok")


class PolicyAutoTask(APIView):

    # tasks associated with policy
    def get(self, request, pk):
        policy = get_object_or_404(Policy, pk=pk)
        return Response(AutoTaskPolicySerializer(policy).data)

    # get status of all tasks
    def patch(self, request, task):
        tasks = AutomatedTask.objects.filter(parent_task=task)
        return Response(PolicyTaskStatusSerializer(tasks, many=True).data)

    # bulk run win tasks associated with policy
    def put(self, request, task):
        tasks = AutomatedTask.objects.filter(parent_task=task)
        run_win_policy_autotask_task.delay([task.id for task in tasks])
        return Response("Affected agent tasks will run shortly")


class PolicyCheck(APIView):
    def get(self, request, pk):
        checks = Check.objects.filter(policy__pk=pk, agent=None)
        return Response(PolicyCheckSerializer(checks, many=True).data)

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
            Policy.objects.filter(pk=pk)
            .prefetch_related(
                "workstation_clients",
                "workstation_sites",
                "server_clients",
                "server_sites",
            )
            .first()
        )

        response["default_server_policy"] = policy.is_default_server_policy
        response["default_workstation_policy"] = policy.is_default_workstation_policy

        response["server_clients"] = ClientSerializer(
            policy.server_clients.all(), many=True
        ).data
        response["workstation_clients"] = ClientSerializer(
            policy.workstation_clients.all(), many=True
        ).data

        filtered_server_sites = list()
        filtered_workstation_sites = list()

        for client in policy.server_clients.all():
            for site in client.sites.all():
                if site not in policy.server_sites.all():
                    filtered_server_sites.append(site)

        response["server_sites"] = SiteSerializer(
            filtered_server_sites + list(policy.server_sites.all()), many=True
        ).data

        for client in policy.workstation_clients.all():
            for site in client.sites.all():
                if site not in policy.workstation_sites.all():
                    filtered_workstation_sites.append(site)

        response["workstation_sites"] = SiteSerializer(
            filtered_workstation_sites + list(policy.workstation_sites.all()), many=True
        ).data

        response["agents"] = AgentHostnameSerializer(
            policy.related_agents(),
            many=True,
        ).data

        return Response(response)

    # update agents, clients, sites to policy
    def post(self, request):

        related_type = request.data["type"]
        pk = request.data["pk"]

        # workstation policy is set
        if (
            "workstation_policy" in request.data
            and request.data["workstation_policy"] != 0
        ):
            policy = get_object_or_404(Policy, pk=request.data["workstation_policy"])

            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)

                # Check and see if workstation policy changed and regenerate policies
                if (
                    not client.workstation_policy
                    or client.workstation_policy
                    and client.workstation_policy.pk != policy.pk
                ):
                    client.workstation_policy = policy
                    client.save()

                    generate_agent_checks_by_location_task.delay(
                        location={"site__client_id": client.id},
                        mon_type="workstation",
                        clear=True,
                        create_tasks=True,
                    )

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)

                # Check and see if workstation policy changed and regenerate policies
                if (
                    not site.workstation_policy
                    or site.workstation_policy
                    and site.workstation_policy.pk != policy.pk
                ):
                    site.workstation_policy = policy
                    site.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site_id": site.id},
                        mon_type="workstation",
                        clear=True,
                        create_tasks=True,
                    )

        # server policy is set
        if "server_policy" in request.data and request.data["server_policy"] != 0:
            policy = get_object_or_404(Policy, pk=request.data["server_policy"])

            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)

                # Check and see if server policy changed and regenerate policies
                if (
                    not client.server_policy
                    or client.server_policy
                    and client.server_policy.pk != policy.pk
                ):
                    client.server_policy = policy
                    client.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site__client_id": client.id},
                        mon_type="server",
                        clear=True,
                        create_tasks=True,
                    )

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)

                # Check and see if server policy changed and regenerate policies
                if (
                    not site.server_policy
                    or site.server_policy
                    and site.server_policy.pk != policy.pk
                ):
                    site.server_policy = policy
                    site.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site_id": site.id},
                        mon_type="server",
                        clear=True,
                        create_tasks=True,
                    )

        # If workstation policy was cleared
        if (
            "workstation_policy" in request.data
            and request.data["workstation_policy"] == 0
        ):
            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)

                # Check if workstation policy is set and update it to None
                if client.workstation_policy:

                    client.workstation_policy = None
                    client.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site__client_id": client.id},
                        mon_type="workstation",
                        clear=True,
                        create_tasks=True,
                    )

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)

                # Check if workstation policy is set and update it to None
                if site.workstation_policy:

                    site.workstation_policy = None
                    site.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site_id": site.id},
                        mon_type="workstation",
                        clear=True,
                        create_tasks=True,
                    )

        # server policy cleared
        if "server_policy" in request.data and request.data["server_policy"] == 0:

            if related_type == "client":
                client = get_object_or_404(Client, pk=pk)

                # Check if server policy is set and update it to None
                if client.server_policy:

                    client.server_policy = None
                    client.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site__client_id": client.id},
                        mon_type="server",
                        clear=True,
                        create_tasks=True,
                    )

            if related_type == "site":
                site = get_object_or_404(Site, pk=pk)
                # Check if server policy is set and update it to None
                if site.server_policy:

                    site.server_policy = None
                    site.save()
                    generate_agent_checks_by_location_task.delay(
                        location={"site_id": site.pk},
                        mon_type="server",
                        clear=True,
                        create_tasks=True,
                    )

        # agent policies
        if related_type == "agent":
            agent = get_object_or_404(Agent, pk=pk)

            if "policy" in request.data and request.data["policy"] != 0:
                policy = Policy.objects.get(pk=request.data["policy"])

                # Check and see if policy changed and regenerate policies
                if not agent.policy or agent.policy and agent.policy.pk != policy.pk:
                    agent.policy = policy
                    agent.save()
                    agent.generate_checks_from_policies(clear=True)
                    agent.generate_tasks_from_policies(clear=True)
            else:
                if agent.policy:
                    agent.policy = None
                    agent.save()
                    agent.generate_checks_from_policies(clear=True)
                    agent.generate_tasks_from_policies(clear=True)

        return Response("ok")

    # view to get policies set on client, site, and workstation
    def patch(self, request):
        related_type = request.data["type"]

        # client, site, or agent pk
        pk = request.data["pk"]

        if related_type == "agent":
            agent = Agent.objects.get(pk=pk)
            return Response(RelatedAgentPolicySerializer(agent).data)

        if related_type == "site":
            site = Site.objects.get(pk=pk)
            return Response(RelatedSitePolicySerializer(site).data)

        if related_type == "client":
            client = Client.objects.get(pk=pk)
            return Response(RelatedClientPolicySerializer(client).data)

        content = {"error": "Data was submitted incorrectly"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)


class UpdatePatchPolicy(APIView):

    # create new patch policy
    def post(self, request):
        policy = get_object_or_404(Policy, pk=request.data["policy"])

        serializer = WinUpdatePolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.policy = policy
        serializer.save()

        return Response("ok")

    # update patch policy
    def put(self, request, patchpolicy):
        policy = get_object_or_404(WinUpdatePolicy, pk=patchpolicy)

        serializer = WinUpdatePolicySerializer(
            instance=policy, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    # bulk reset agent patch policy
    def patch(self, request):

        agents = None
        if "client" in request.data:
            agents = Agent.objects.filter(site__client_id=request.data["client"])
        elif "site" in request.data:
            agents = Agent.objects.filter(site_id=request.data["site"])
        else:
            agents = Agent.objects.all()

        for agent in agents:
            winupdatepolicy = agent.winupdatepolicy.get()
            winupdatepolicy.critical = "inherit"
            winupdatepolicy.important = "inherit"
            winupdatepolicy.moderate = "inherit"
            winupdatepolicy.low = "inherit"
            winupdatepolicy.other = "inherit"
            winupdatepolicy.run_time_frequency = "inherit"
            winupdatepolicy.reboot_after_install = "inherit"
            winupdatepolicy.reprocess_failed_inherit = True
            winupdatepolicy.save(
                update_fields=[
                    "critical",
                    "important",
                    "moderate",
                    "low",
                    "other",
                    "run_time_frequency",
                    "reboot_after_install",
                    "reprocess_failed_inherit",
                ]
            )

        return Response("ok")

    # delete patch policy
    def delete(self, request, patchpolicy):
        get_object_or_404(WinUpdatePolicy, pk=patchpolicy).delete()

        return Response("ok")
