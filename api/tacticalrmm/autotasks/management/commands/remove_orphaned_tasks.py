from django.core.management.base import BaseCommand
from django.conf import settings
from agents.models import Agent
from autotasks.tasks import remove_orphaned_win_tasks


class Command(BaseCommand):
    help = "Checks for orphaned tasks on all agents and removes them"

    def handle(self, *args, **kwargs):

        for agent in Agent.objects.all():
            remove_orphaned_win_tasks.delay(agent.pk)

        self.stdout.write(
            "The task has been initiated. Check the Debug Log in the UI for progress."
        )
