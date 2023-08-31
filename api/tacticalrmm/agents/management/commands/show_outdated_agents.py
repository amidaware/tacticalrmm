from django.conf import settings
from django.core.management.base import BaseCommand

from agents.models import Agent
from tacticalrmm.constants import AGENT_STATUS_ONLINE, ONLINE_AGENTS


class Command(BaseCommand):
    help = "Shows online agents that are not on the latest version"

    def handle(self, *args, **kwargs):
        only = ONLINE_AGENTS + ("hostname",)
        q = Agent.objects.exclude(version=settings.LATEST_AGENT_VER).only(*only)
        agents = [i for i in q if i.status == AGENT_STATUS_ONLINE]
        for agent in agents:
            self.stdout.write(
                self.style.SUCCESS(f"{agent.hostname} - v{agent.version}")
            )
