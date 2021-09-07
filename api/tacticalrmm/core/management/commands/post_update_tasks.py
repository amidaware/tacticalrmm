from django.core.management.base import BaseCommand

from logs.models import PendingAction
from scripts.models import Script
from accounts.models import User


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        # remove task pending actions. deprecated 4/20/2021
        PendingAction.objects.filter(action_type="taskaction").delete()

        # load community scripts into the db
        Script.load_community_scripts()

        # make sure installer user is set to block_dashboard_logins
        if User.objects.filter(is_installer_user=True).exists():
            for user in User.objects.filter(is_installer_user=True):
                user.block_dashboard_login = True
                user.save()
