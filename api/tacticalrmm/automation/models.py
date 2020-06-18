from django.db import models
from agents.models import Agent
from clients.models import Site, Client


class Policy(models.Model):
    name = models.CharField(max_length=255, unique=True)
    desc = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=False)
    enforced = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def related_agents(self):
        explicit_agents = self.agents.all()
        explicit_clients = self.clients.all()
        explicit_sites = self.sites.all()

        filtered_sites_ids = list()
        client_ids = list()

        for site in explicit_sites:
            if site.client not in explicit_clients:
                filtered_sites_ids.append(site.site)

        for client in explicit_clients:
            client_ids.append(client.client)
            for site in client.sites.all():
                filtered_sites_ids.append(site.site)

        return Agent.objects.filter(
            models.Q(pk__in=explicit_agents.only("pk"))
            | models.Q(site__in=filtered_sites_ids)
            | models.Q(client__in=client_ids)
        ).distinct()

    @staticmethod
    def cascade_policy_checks(agent):
        # Get checks added to agent directly
        agent_checks = list(agent.agentchecks.filter(managed_by_policy=False))

        # Get policies applied to agent and agent site and client
        client = Client.objects.get(client=agent.client)
        site = Site.objects.filter(client=client).get(site=agent.site)

        client_policy = client.policy
        site_policy = site.policy
        agent_policy = agent.policy

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
                if check.script not in added_script_checks:
                    added_script_checks.append(check.script)
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

        return (
            diskspace_checks
            + ping_checks
            + cpuload_checks
            + memory_checks
            + winsvc_checks
            + script_checks
            + eventlog_checks
        )

    @staticmethod
    def generate_policy_checks(agent):
        checks = Policy.cascade_policy_checks(agent)

        if checks:
            for check in checks:
                check.create_policy_check(agent)


class PolicyExclusions(models.Model):
    policy = models.ForeignKey(
        Policy, related_name="exclusions", on_delete=models.CASCADE
    )
    agents = models.ManyToManyField(Agent, related_name="policy_exclusions")
    sites = models.ManyToManyField(Site, related_name="policy_exclusions")
