import uuid
from django.test import TestCase, override_settings
from model_bakery import baker
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from core.models import CoreSettings


class TacticalTestCase(TestCase):
    def authenticate(self):
        self.john = User(username="john")
        self.john.is_superuser = True
        self.john.set_password("hunter2")
        self.john.save()
        self.alice = User(username="alice")
        self.alice.is_superuser = True
        self.alice.set_password("hunter2")
        self.alice.save()
        self.client_setup()
        self.client.force_authenticate(user=self.john)

        User.objects.create_user(  # type: ignore
            username=uuid.uuid4().hex,
            is_installer_user=True,
            password=User.objects.make_random_password(60),  # type: ignore
        )

    def setup_agent_auth(self, agent):
        agent_user = User.objects.create_user(
            username=agent.agent_id,
            password=User.objects.make_random_password(60),
        )
        Token.objects.create(user=agent_user)

    def client_setup(self):
        self.client = APIClient()

    # fixes tests waiting 2 minutes for mesh token to appear
    @override_settings(
        MESH_TOKEN_KEY="41410834b8bb4481446027f87d88ec6f119eb9aa97860366440b778540c7399613f7cabfef4f1aa5c0bd9beae03757e17b2e990e5876b0d9924da59bdf24d3437b3ed1a8593b78d65a72a76c794160d9"
    )
    def setup_coresettings(self):
        self.coresettings = CoreSettings.objects.create()

    def check_not_authenticated(self, method, url):
        self.client.logout()
        switch = {
            "get": self.client.get(url),
            "post": self.client.post(url),
            "put": self.client.put(url),
            "patch": self.client.patch(url),
            "delete": self.client.delete(url),
        }
        r = switch.get(method)
        self.assertEqual(r.status_code, 401)

    def create_checks(self, policy=None, agent=None, script=None):

        if not policy and not agent:
            return

        # will create 1 of every check and associate it with the policy object passed
        check_recipes = [
            "checks.diskspace_check",
            "checks.ping_check",
            "checks.cpuload_check",
            "checks.memory_check",
            "checks.winsvc_check",
            "checks.script_check",
            "checks.eventlog_check",
        ]

        checks = list()
        for recipe in check_recipes:
            if not script:
                checks.append(baker.make_recipe(recipe, policy=policy, agent=agent))
            else:
                checks.append(
                    baker.make_recipe(recipe, policy=policy, agent=agent, script=script)
                )
        return checks
