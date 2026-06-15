from time import sleep

from django.core.management.base import BaseCommand

from agents.models import Agent
from agents.utils import get_agent_url
from core.utils import get_mesh_ws_url, token_is_valid
from tacticalrmm.constants import AGENT_DEFER


class Command(BaseCommand):
    help = "Reinstalls the tactical and meshagent services"

    def handle(self, *args, **kwargs) -> None:
        agents = Agent.objects.defer(*AGENT_DEFER)
        uri = get_mesh_ws_url()
        code_token, _ = token_is_valid()

        for agent in agents:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Restarting Tactical Agent Service on {agent.hostname}"
                )
            )
            agent_url = get_agent_url(
                goarch=agent.goarch, plat=agent.plat, token=code_token
            )
            agent.recover("tacagent", uri, wait=False, agent_url=agent_url)

        self.stdout.write(self.style.WARNING("Waiting 10 seconds..."))
        sleep(10)

        for agent in agents:
            self.stdout.write(
                self.style.SUCCESS(f"Restarting MeshAgent Service on {agent.hostname}")
            )
            agent.recover("mesh", "", wait=False)
