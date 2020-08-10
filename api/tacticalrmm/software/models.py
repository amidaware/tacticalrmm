from django.db import models

from agents.models import Agent


class ChocoSoftware(models.Model):
    chocos = models.JSONField()
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

    @classmethod
    def combine_all(cls):
        from .serializers import ChocoSoftwareSerializer

        chocos = cls.objects.all()
        combined = []
        for i in chocos:
            combined.extend(ChocoSoftwareSerializer(i).data["chocos"])

        # remove duplicates
        return [dict(t) for t in {tuple(d.items()) for d in combined}]

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
