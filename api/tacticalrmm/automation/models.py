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
