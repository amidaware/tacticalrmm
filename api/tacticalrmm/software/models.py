from django.db import models

from agents.models import Agent


class ChocoSoftware(models.Model):
    chocos = models.JSONField()
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        from .serializers import ChocoSoftwareSerializer

        return (
            str(len(ChocoSoftwareSerializer(self).data["chocos"])) + f" - {self.added}"
        )


class ChocoLog(models.Model):
    agent = models.ForeignKey(Agent, related_name="chocolog", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    message = models.TextField()
    installed = models.BooleanField(default=False)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent.hostname} | {self.name} | {self.time}"


class InstalledSoftware(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    software = models.JSONField()

    def __str__(self):
        return self.agent.hostname
