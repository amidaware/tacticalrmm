from django.db import models
from agents.models import Agent
from clients.models import Site, Client
from core.models import CoreSettings
from logs.models import BaseAuditModel


class Policy(BaseAuditModel):
    name = models.CharField(max_length=255, unique=True)
    desc = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=False)
    enforced = models.BooleanField(default=False)

    @property
    def is_default_server_policy(self):
        return self.default_server_policy.exists()

    @property
    def is_default_workstation_policy(self):
        return self.default_workstation_policy.exists()

    def __str__(self):
        return self.name

    def related_agents(self):
        return self.get_related("server") | self.get_related("workstation")

    def get_related(self, mon_type):
        explicit_agents = self.agents.filter(monitoring_type=mon_type)
        explicit_clients = getattr(self, f"{mon_type}_clients").all()
        explicit_sites = getattr(self, f"{mon_type}_sites").all()

        filtered_agents_pks = Policy.objects.none()

        filtered_agents_pks |= Agent.objects.filter(
            site__in=[
                site for site in explicit_sites if site.client not in explicit_clients
            ],
            monitoring_type=mon_type,
        ).values_list("pk", flat=True)

        filtered_agents_pks |= Agent.objects.filter(
            site__client__in=[client for client in explicit_clients],
            monitoring_type=mon_type,
        ).values_list("pk", flat=True)

        return Agent.objects.filter(
            models.Q(pk__in=filtered_agents_pks)
            | models.Q(pk__in=explicit_agents.only("pk"))
        )

    @staticmethod
    def serialize(policy):
        # serializes the policy and returns json
        from .serializers import PolicySerializer

        return PolicySerializer(policy).data

    @staticmethod
    def cascade_policy_tasks(agent):
        # List of all tasks to be applied
        tasks = list()
        added_task_pks = list()

        agent_tasks_parent_pks = [
            task.parent_task for task in agent.autotasks.filter(managed_by_policy=True)
        ]

        # Get policies applied to agent and agent site and client
        client = agent.client
        site = agent.site

        default_policy = None
        client_policy = None
        site_policy = None
        agent_policy = agent.policy

        # Get the Client/Site policy based on if the agent is server or workstation
        if agent.monitoring_type == "server":
            default_policy = CoreSettings.objects.first().server_policy
            client_policy = client.server_policy
            site_policy = site.server_policy
        else:
            default_policy = CoreSettings.objects.first().workstation_policy
            client_policy = client.workstation_policy
            site_policy = site.workstation_policy

        if agent_policy and agent_policy.active:
            for task in agent_policy.autotasks.all():
                if task.pk not in added_task_pks:
                    tasks.append(task)
                    added_task_pks.append(task.pk)
        if site_policy and site_policy.active:
            for task in site_policy.autotasks.all():
                if task.pk not in added_task_pks:
                    tasks.append(task)
                    added_task_pks.append(task.pk)
        if client_policy and client_policy.active:
            for task in client_policy.autotasks.all():
                if task.pk not in added_task_pks:
                    tasks.append(task)
                    added_task_pks.append(task.pk)

        if default_policy and default_policy.active:
            for task in default_policy.autotasks.all():
                if task.pk not in added_task_pks:
                    tasks.append(task)
                    added_task_pks.append(task.pk)

        return [task for task in tasks if task.pk not in agent_tasks_parent_pks]

    @staticmethod
    def cascade_policy_checks(agent):
        # Get checks added to agent directly
        agent_checks = list(agent.agentchecks.filter(managed_by_policy=False))

        agent_checks_parent_pks = [
            check.parent_check
            for check in agent.agentchecks.filter(managed_by_policy=True)
        ]

        # Get policies applied to agent and agent site and client
        client = agent.client
        site = agent.site

        default_policy = None
        client_policy = None
        site_policy = None
        agent_policy = agent.policy

        if agent.monitoring_type == "server":
            default_policy = CoreSettings.objects.first().server_policy
            client_policy = client.server_policy
            site_policy = site.server_policy
        else:
            default_policy = CoreSettings.objects.first().workstation_policy
            client_policy = client.workstation_policy
            site_policy = site.workstation_policy

        # Used to hold the policies that will be applied and the order in which they are applied
        # Enforced policies are applied first
        enforced_checks = list()
        policy_checks = list()

        if agent_policy and agent_policy.active:
            if agent_policy.enforced:
                for check in agent_policy.policychecks.all():
                    enforced_checks.append(check)
            else:
                for check in agent_policy.policychecks.all():
                    policy_checks.append(check)

        if site_policy and site_policy.active:
            if site_policy.enforced:
                for check in site_policy.policychecks.all():
                    enforced_checks.append(check)
            else:
                for check in site_policy.policychecks.all():
                    policy_checks.append(check)

        if client_policy and client_policy.active:
            if client_policy.enforced:
                for check in client_policy.policychecks.all():
                    enforced_checks.append(check)
            else:
                for check in client_policy.policychecks.all():
                    policy_checks.append(check)

        if default_policy and default_policy.active:
            if default_policy.enforced:
                for check in default_policy.policychecks.all():
                    enforced_checks.append(check)
            else:
                for check in default_policy.policychecks.all():
                    policy_checks.append(check)

        # Sorted Checks already added
        added_diskspace_checks = list()
        added_ping_checks = list()
        added_winsvc_checks = list()
        added_script_checks = list()
        added_eventlog_checks = list()
        added_cpuload_checks = list()
        added_memory_checks = list()

        # Lists all agent and policy checks that will be created
        diskspace_checks = list()
        ping_checks = list()
        winsvc_checks = list()
        script_checks = list()
        eventlog_checks = list()
        cpuload_checks = list()
        memory_checks = list()

        # Loop over checks in with enforced policies first, then non-enforced policies
        for check in enforced_checks + agent_checks + policy_checks:
            if check.check_type == "diskspace":
                # Check if drive letter was already added
                if check.disk not in added_diskspace_checks:
                    added_diskspace_checks.append(check.disk)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        diskspace_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "ping":
                # Check if IP/host was already added
                if check.ip not in added_ping_checks:
                    added_ping_checks.append(check.ip)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        ping_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "cpuload":
                # Check if cpuload list is empty
                if not added_cpuload_checks:
                    added_cpuload_checks.append(check)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        cpuload_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "memory":
                # Check if memory check list is empty
                if not added_memory_checks:
                    added_memory_checks.append(check)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        memory_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "winsvc":
                # Check if service name was already added
                if check.svc_name not in added_winsvc_checks:
                    added_winsvc_checks.append(check.svc_name)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        winsvc_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "script":
                # Check if script id was already added
                if check.script.id not in added_script_checks:
                    added_script_checks.append(check.script.id)
                    # Dont create the check if it is an agent check
                    if not check.agent:
                        script_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

            if check.check_type == "eventlog":
                # Check if events were already added
                if [check.log_name, check.event_id] not in added_eventlog_checks:
                    added_eventlog_checks.append([check.log_name, check.event_id])
                    if not check.agent:
                        eventlog_checks.append(check)
                elif check.agent:
                    check.overriden_by_policy = True
                    check.save()

        final_list = (
            diskspace_checks
            + ping_checks
            + cpuload_checks
            + memory_checks
            + winsvc_checks
            + script_checks
            + eventlog_checks
        )

        return [
            check for check in final_list if check.pk not in agent_checks_parent_pks
        ]

    @staticmethod
    def generate_policy_checks(agent):
        checks = Policy.cascade_policy_checks(agent)

        if checks:
            for check in checks:
                check.create_policy_check(agent)

    @staticmethod
    def generate_policy_tasks(agent):
        tasks = Policy.cascade_policy_tasks(agent)

        if tasks:
            for task in tasks:
                task.create_policy_task(agent)
