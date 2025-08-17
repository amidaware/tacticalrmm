import base64

from django.core.management.base import BaseCommand

from accounts.models import User
from agents.models import Agent
from autotasks.models import AutomatedTask
from checks.models import Check, CheckHistory
from core.models import CoreSettings
from core.tasks import remove_orphaned_history_results, sync_mesh_perms_task
from scripts.models import Script
from tacticalrmm.constants import AGENT_DEFER, ScriptType


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write("Running post update tasks")

        # load community scripts into the db
        Script.load_community_scripts()

        # make sure installer user is set to block_dashboard_logins
        if User.objects.filter(is_installer_user=True).exists():
            for user in User.objects.filter(is_installer_user=True):
                user.block_dashboard_login = True
                user.save()

        # convert script base64 field to text field
        user_scripts = Script.objects.exclude(script_type=ScriptType.BUILT_IN).filter(
            script_body=""
        )
        for script in user_scripts:
            # decode base64 string
            script.script_body = base64.b64decode(
                script.code_base64.encode("ascii", "ignore")
            ).decode("ascii", "ignore")
            # script.hash_script_body()  # also saves script
            script.save(update_fields=["script_body"])

        # Remove policy checks and tasks on agents and check
        AutomatedTask.objects.filter(managed_by_policy=True).delete()
        Check.objects.filter(managed_by_policy=True).delete()
        CheckHistory.objects.filter(agent_id=None).delete()

        # set goarch for older windows agents
        for agent in Agent.objects.defer(*AGENT_DEFER):
            if not agent.goarch:
                if agent.arch == "64":
                    agent.goarch = "amd64"
                elif agent.arch == "32":
                    agent.goarch = "386"
                else:
                    agent.goarch = "amd64"

                agent.save(update_fields=["goarch"])

        self.stdout.write(
            self.style.SUCCESS("Checking for orphaned history results...")
        )
        count = remove_orphaned_history_results()
        if count:
            self.stdout.write(
                self.style.SUCCESS(f"Removed {count} orphaned history results.")
            )

        core = CoreSettings.objects.first()
        if core.sync_mesh_with_trmm:
            self.stdout.write(
                self.style.SUCCESS(
                    "Syncing trmm users/permissions with meshcentral, this might take a long time...please wait..."
                )
            )
            sync_mesh_perms_task()

        self.stdout.write("Post update tasks finished")
