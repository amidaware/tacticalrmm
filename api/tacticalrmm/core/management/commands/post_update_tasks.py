from django.core.management.base import BaseCommand

from logs.models import PendingAction
from scripts.models import Script


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        # remove task pending actions. deprecated 4/20/2021
        PendingAction.objects.filter(action_type="taskaction").delete()

        # load community scripts into the db
        Script.load_community_scripts()
