import base64
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
import datetime as dt

from logs.models import PendingAction
from scripts.models import Script
from autotasks.models import AutomatedTask
from accounts.models import User


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        self.stdout.write("Running post update tasks")

        # remove task pending actions. deprecated 4/20/2021
        PendingAction.objects.filter(action_type="taskaction").delete()

        # load community scripts into the db
        Script.load_community_scripts()

        # make sure installer user is set to block_dashboard_logins
        if User.objects.filter(is_installer_user=True).exists():
            for user in User.objects.filter(is_installer_user=True):
                user.block_dashboard_login = True
                user.save()

        # convert script base64 field to text field
        user_scripts = Script.objects.exclude(script_type="builtin").filter(
            script_body=""
        )
        for script in user_scripts:
            # decode base64 string
            script.script_body = base64.b64decode(
                script.code_base64.encode("ascii", "ignore")
            ).decode("ascii", "ignore")
            # script.hash_script_body()  # also saves script
            script.save(update_fields=["script_body"])

        # convert autotask to the new format
        for task in AutomatedTask.objects.all():
            try:
                edited = False

                # convert scheduled task_type
                if task.task_type == "scheduled":
                    task.task_type = "daily"
                    task.run_time_date = make_aware(
                        dt.datetime.strptime(task.run_time_minute, "%H:%M")
                    )
                    task.daily_interval = 1
                    edited = True

                # convert actions
                if not task.actions:
                    task.actions = [
                        {
                            "type": "script",
                            "script": task.script.pk,
                            "script_args": task.script_args,
                            "timeout": task.timeout,
                            "name": task.script.name,
                        }
                    ]
                    edited = True

                if edited:
                    task.save()
            except:
                continue

        self.stdout.write("Post update tasks finished")
