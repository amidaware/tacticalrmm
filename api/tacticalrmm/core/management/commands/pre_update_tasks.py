from time import sleep

from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, before migrations"

    def handle(self, *args, **kwargs):
        # adding this now for future updates
        pass
