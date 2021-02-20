from django.core.management.base import BaseCommand

from agents.models import Agent
from autotasks.tasks import remove_orphaned_win_tasks


class Command(BaseCommand):
    help = "Checks for orphaned tasks on all agents and removes them"

    def handle(self, *args, **kwargs):
        agents = Agent.objects.only("pk", "last_seen", "overdue_time", "offline_time")
        online = [i for i in agents if i.status == "online"]
        for agent in online:
            remove_orphaned_win_tasks.delay(agent.pk)

        self.stdout.write(
            self.style.SUCCESS(
                "The task has been initiated. Check the Debug Log in the UI for progress."
            )
        )
