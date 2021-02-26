from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Find all agents that have a certain software installed"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)

    def handle(self, *args, **kwargs):
        search = kwargs["name"].lower()

        agents = Agent.objects.all()
        for agent in agents:
            sw = agent.installedsoftware_set.first().software
            for i in sw:
                if search in i["name"].lower():
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Found {i['name']} installed on {agent.hostname}"
                        )
                    )
                    break
