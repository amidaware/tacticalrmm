from django.db import models
from agents.models import Agent


class Client(models.Model):
    client = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.client

    @property
    def has_failing_checks(self):

        agents = Agent.objects.filter(client=self.client)
        for agent in agents:
            if agent.checks["has_failing_checks"]:
                return True

        return False


class Site(models.Model):
    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    site = models.CharField(max_length=255)

    def __str__(self):
        return self.site

    @property
    def has_failing_checks(self):

        agents = Agent.objects.filter(client=self.client.client).filter(site=self.site)
        for agent in agents:
            if agent.checks["has_failing_checks"]:
                return True

        return False


def validate_name(name):
    if "|" in name:
        return False
    else:
        return True
