from django.core.management.base import BaseCommand
from core.models import CoreSettings


class Command(BaseCommand):
    help = "Populates the global site settings on first install"

    def handle(self, *args, **kwargs):
        CoreSettings().save()
        self.stdout.write("Core db populated")
