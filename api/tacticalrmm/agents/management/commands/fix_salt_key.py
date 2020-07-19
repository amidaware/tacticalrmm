from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Changes existing agents salt_id from a property to a model field"

    def handle(self, *args, **kwargs):
        agents = Agent.objects.filter(salt_id=None)
        for agent in agents:
            self.stdout.write(
                self.style.SUCCESS(f"Setting salt_id on {agent.hostname}")
            )
            agent.salt_id = f"{agent.hostname}-{agent.pk}"
            agent.save(update_fields=["salt_id"])
