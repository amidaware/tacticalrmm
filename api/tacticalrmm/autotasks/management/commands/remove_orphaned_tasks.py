from django.core.management.base import BaseCommand

from autotasks.tasks import remove_orphaned_win_tasks


class Command(BaseCommand):
    help = "Checks for orphaned tasks on all agents and removes them"

    def handle(self, *args, **kwargs):
        remove_orphaned_win_tasks.s()

        self.stdout.write(
            self.style.SUCCESS(
                "The task has been initiated. Check the Debug Log in the UI for progress."
            )
        )
