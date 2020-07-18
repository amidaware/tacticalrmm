import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings

from software.models import ChocoSoftware


class Command(BaseCommand):
    help = "Populates database with initial software"

    def handle(self, *args, **kwargs):
        with open(os.path.join(settings.BASE_DIR, "software/chocos.json")) as f:
            chocos = json.load(f)

        ChocoSoftware(chocos=chocos).save()
        self.stdout.write("Chocos saved to db")
