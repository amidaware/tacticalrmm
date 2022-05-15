from django.conf import settings
from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Shows online agents that are not on the latest version"

    def handle(self, *args, **kwargs):
        q = Agent.objects.exclude(version=settings.LATEST_AGENT_VER).only(
            "pk", "version", "last_seen", "overdue_time", "offline_time"
        )
        agents = [i for i in q if i.status == "online"]
        for agent in agents:
            self.stdout.write(
                self.style.SUCCESS(f"{agent.hostname} - v{agent.version}")
            )
