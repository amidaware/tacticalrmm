from django.core.management.base import BaseCommand

from agents.models import Agent
from tacticalrmm.constants import AGENT_DEFER


class Command(BaseCommand):
    help = "Find all agents that have a certain service installed"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)

    def handle(self, *args, **kwargs):
        search = kwargs["name"].lower()

        agents = Agent.objects.defer(*AGENT_DEFER)
        for agent in agents:
            try:
                for svc in agent.services:
                    if (
                        search in svc["name"].lower()
                        or search in svc["display_name"].lower()
                    ):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{agent.hostname} - {svc['name']} ({svc['display_name']}) - {svc['status']}"
                            )
                        )
            except:
                continue
