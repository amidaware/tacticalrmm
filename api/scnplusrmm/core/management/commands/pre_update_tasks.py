from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.utils import clear_entire_cache


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, before migrations"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Cleaning the cache"))
        clear_entire_cache()
        self.stdout.write(self.style.SUCCESS("Cache was cleared!"))
        try:
            call_command("fix_dupe_agent_customfields")
        except:
            pass
