from django.db import models
from django.contrib.postgres.fields import JSONField

from agents.models import Agent


class ChocoSoftware(models.Model):
    chocos = JSONField()
    added = models.DateTimeField(auto_now_add=True)

    @classmethod
    def sort_by_highest(cls):
        from .serializers import ChocoSoftwareSerializer

        chocos = cls.objects.all()
        sizes = [
            {"size": len(ChocoSoftwareSerializer(i).data["chocos"]), "pk": i.pk}
            for i in chocos
        ]
        biggest = max(range(len(sizes)), key=lambda index: sizes[index]["size"])
        return int(sizes[biggest]["pk"])


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
    software = JSONField()

    def __str__(self):
        return self.agent.hostname
