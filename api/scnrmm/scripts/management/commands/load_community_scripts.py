from django.core.management.base import BaseCommand

from scripts.models import Script


class Command(BaseCommand):
    help = "Loads community scripts into the database"

    def handle(self, *args, **kwargs):
        self.stdout.write("Syncing community scripts...")
        Script.load_community_scripts()
        self.stdout.write("Community scripts synced successfully")
