import base64
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from agents.models import Agent
from autotasks.models import AutomatedTask
from checks.models import Check, CheckHistory
from core.models import CoreSettings
from core.tasks import remove_orphaned_history_results, sync_mesh_perms_task
from scripts.models import Script
from tacticalrmm.constants import AGENT_DEFER, ScriptType
from tacticalrmm.helpers import get_webdomain


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write("Running post update tasks")

        # for 0.20.0 release
        if not settings.DOCKER_BUILD:
            needs_frontend = False
            frontend_domain = get_webdomain().split(":")[0]

            local_settings = os.path.join(
                settings.BASE_DIR, "tacticalrmm", "local_settings.py"
            )

            with open(local_settings) as f:
                lines = f.readlines()

            modified_lines = []
            for line in lines:
                if line.strip().startswith("ALLOWED_HOSTS"):
                    exec(line, globals())

                    if frontend_domain not in settings.ALLOWED_HOSTS:
                        needs_frontend = True
                        settings.ALLOWED_HOSTS.append(frontend_domain)

                    line = f"ALLOWED_HOSTS = {settings.ALLOWED_HOSTS}\n"

                modified_lines.append(line)

            if needs_frontend:
                backup = Path.home() / (Path("local_settings_0.20.0.bak"))
                shutil.copy2(local_settings, backup)
                with open(local_settings, "w") as f:
                    f.writelines(modified_lines)

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
