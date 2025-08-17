from contextlib import suppress

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from core.models import CoreSettings


class Command(BaseCommand):
    help = "Populates the global site settings on first install"

    def handle(self, *args, **kwargs):
        # can only be 1 instance of this. Prevents error when rebuilding docker container
        with suppress(ValidationError):
            CoreSettings().save()
            self.stdout.write("Core db populated")
