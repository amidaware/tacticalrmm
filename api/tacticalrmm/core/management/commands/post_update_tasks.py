import base64

from accounts.models import User
from agents.models import Agent
from autotasks.models import AutomatedTask
from checks.models import Check, CheckHistory
from django.core.management.base import BaseCommand
from scripts.models import Script

from tacticalrmm.constants import AGENT_DEFER


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

        self.stdout.write("Post update tasks finished")
