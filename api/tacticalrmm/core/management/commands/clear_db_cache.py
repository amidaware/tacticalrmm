from django.core.management.base import BaseCommand

from core.utils import clear_entire_cache


class Command(BaseCommand):
    help = "Clear db cache"

    def handle(self, *args, **kwargs):
        clear_entire_cache()
        self.stdout.write(self.style.SUCCESS("Cache was cleared!"))
