from django.db import models
from agents.models import Agent
from clients.models import Site, Client

class Policy(models.Model):
    name = models.CharField(max_length=255, unique=True)
    desc = models.CharField(max_length=255)
    active = models.BooleanField(default=False)
    agents = models.ManyToManyField(Agent, related_name="policies")
    sites = models.ManyToManyField(Site, related_name="policies")
    clients = models.ManyToManyField(Client, related_name="policies")

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

        site_agents = Agent.objects.filter(site__in=filtered_sites_ids)
        client_agents = Agent.objects.filter(client__in=client_ids)
        
        # Combine querysets and remove duplicates
        return explicit_agents.union(site_agents, client_agents)
