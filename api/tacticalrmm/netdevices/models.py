import random

from django.contrib.postgres.fields import ArrayField
from django.db import models

from tacticalrmm.constants import AGENT_STATUS_ONLINE, AgentMonType

PROTOCOL_CHOICES = [
    ("https", "HTTPS"),
    ("http", "HTTP"),
    ("ssh", "SSH"),
    ("telnet", "Telnet"),
]


class NetworkDevice(models.Model):
    site = models.ForeignKey(
        "clients.Site",
        related_name="network_devices",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, default="https"
    )
    ip_address = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=443)
    description = models.TextField(null=True, blank=True, default="")
    # ordered list of agent_id strings, highest preference first
    preferred_agents = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
    )
    created_time = models.DateTimeField(auto_now_add=True)
    modified_time = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.protocol}://{self.ip_address}:{self.port})"

    @property
    def client(self):
        return self.site.client

    def candidate_agents(self):
        """Ordered list of ONLINE agents to try, highest preference first:

        1. ONLINE agents from ``preferred_agents`` in preference order.
        2. Then other online agents in the device's site (servers first), then
           the client (servers first) - shuffled within each group.
        """
        from agents.models import Agent

        ordered = []
        seen = set()

        # 1) preferred agents, in order
        if self.preferred_agents:
            by_id = {
                a.agent_id: a
                for a in Agent.objects.filter(agent_id__in=self.preferred_agents)
            }
            for agent_id in self.preferred_agents:
                a = by_id.get(agent_id)
                if a and a.status == AGENT_STATUS_ONLINE and a.agent_id not in seen:
                    ordered.append(a)
                    seen.add(a.agent_id)

        # 2) fallback pools (site then client), servers before workstations
        for scope in (
            Agent.objects.filter(site=self.site),
            Agent.objects.filter(site__client=self.site.client),
        ):
            online = [
                a
                for a in scope
                if a.status == AGENT_STATUS_ONLINE and a.agent_id not in seen
            ]
            servers = [a for a in online if a.monitoring_type == AgentMonType.SERVER]
            workstations = [
                a for a in online if a.monitoring_type != AgentMonType.SERVER
            ]
            random.shuffle(servers)
            random.shuffle(workstations)
            for a in servers + workstations:
                ordered.append(a)
                seen.add(a.agent_id)

        return ordered

    def resolve_agent(self):
        """First online candidate (no reachability test)."""
        agents = self.candidate_agents()
        return agents[0] if agents else None

    def resolve_reachable_agent(self, max_tries=5, timeout=5):
        """Return (agent, tried_hostnames). Probes candidate agents concurrently
        and returns the first that can actually reach the device. A successful
        agent is cached briefly so repeat connects are instant. Falls back to the
        first online candidate if none pass the reachability probe."""
        from django.core.cache import cache

        from agents.web_proxy import agent_can_reach

        candidates = [
            a for a in self.candidate_agents() if a.hex_mesh_node_id != "error"
        ]
        if not candidates:
            return None, []

        candidates = candidates[:max_tries]
        tried = [a.hostname for a in candidates]
        by_id = {a.agent_id: a for a in candidates}

        # 1) reuse the last agent we confirmed could reach this device (if it's
        #    still an online candidate) -> skip probing entirely.
        ck = f"netdev_reach:{self.pk}:{self.protocol}:{self.ip_address}:{self.port}"
        cached_id = cache.get(ck)
        if cached_id and cached_id in by_id:
            return by_id[cached_id], tried

        # 2) probe candidates one at a time (the preferred/first agent normally
        #    answers in well under a second). Sequential on purpose: firing many
        #    simultaneous tunnels at the MeshCentral relay causes contention and
        #    is actually slower. A short timeout bounds the cost of a dead agent.
        for agent in candidates:
            if agent_can_reach(
                agent.hex_mesh_node_id, self.ip_address, self.port,
                protocol=self.protocol, timeout=timeout,
            ):
                cache.set(ck, agent.agent_id, 300)  # remember good agent for 5 min
                return agent, tried
        return (candidates[0] if candidates else None), tried
