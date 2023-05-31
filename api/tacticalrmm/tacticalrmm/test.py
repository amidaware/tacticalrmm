import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.test import TestCase, modify_settings, override_settings
from model_bakery import baker
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from agents.models import Agent
from automation.models import Policy
from core.models import CoreSettings
from tacticalrmm.constants import CustomFieldModel, CustomFieldType
from tacticalrmm.helpers import make_random_password

if TYPE_CHECKING:
    from checks.models import Check
    from clients.models import Client, Site
    from core.models import CustomField
    from scripts.models import Script

TEST_CACHE = {
    "default": {
        "BACKEND": "tacticalrmm.cache.TacticalDummyCache",
    }
}


@override_settings(
    CACHES=TEST_CACHE,
    DEBUG=False,
    ADMIN_ENABLED=False,
)
@modify_settings(
    INSTALLED_APPS={
        "remove": [
            "django.contrib.admin",
            "django.contrib.messages",
            "django_extensions",
            "silk",
        ]
    },
    MIDDLEWARE={
        "remove": [
            "silk.middleware.SilkyMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ]
    },
)
class TacticalTestCase(TestCase):
    client: APIClient

    def authenticate(self) -> None:
        self.john = User(username="john")
        self.john.is_superuser = True
        self.john.set_password("hunter2")
        self.john.save()
        self.alice = User(username="alice")
        self.alice.is_superuser = True
        self.alice.set_password("hunter2")
        self.alice.save()
        self.setup_client()
        self.client.force_authenticate(user=self.john)

        User.objects.create_user(  # type: ignore
            username=uuid.uuid4().hex,
            is_installer_user=True,
            password=make_random_password(len=60),  # type: ignore
        )

    def setup_client(self) -> None:
        self.client = APIClient()

    def setup_agent_auth(self, agent: "Agent") -> None:
        agent_user = User.objects.create_user(  # type: ignore
            username=agent.agent_id,
            password=make_random_password(len=60),  # type: ignore
        )
        Token.objects.create(user=agent_user)

    # fixes tests waiting 2 minutes for mesh token to appear
    @override_settings(
        MESH_TOKEN_KEY="41410834b8bb4481446027f87d88ec6f119eb9aa97860366440b778540c7399613f7cabfef4f1aa5c0bd9beae03757e17b2e990e5876b0d9924da59bdf24d3437b3ed1a8593b78d65a72a76c794160d9",
    )
    def setup_coresettings(self) -> None:
        self.coresettings = CoreSettings.objects.create()

    def check_not_authenticated(self, method: str, url: str) -> None:
        self.client.logout()

        r = getattr(self.client, method)(url)
        self.assertEqual(r.status_code, 401)

    def create_checks(
        self, parent: "Union[Policy, Agent]", script: "Optional[Script]" = None
    ) -> "List[Check]":
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

        parent_obj = {}
        if isinstance(parent, Policy):
            parent_obj["policy"] = parent
        else:
            parent_obj["agent"] = parent
        checks = []
        for recipe in check_recipes:
            if not script:
                checks.append(baker.make_recipe(recipe, **parent_obj))
            else:
                checks.append(baker.make_recipe(recipe, **parent_obj, script=script))
        return checks

    def check_not_authorized(
        self, method: str, url: str, data: Optional[Dict[Any, Any]] = {}
    ) -> None:
        try:
            r = getattr(self.client, method)(url, data, format="json")
            self.assertEqual(r.status_code, 403)
        except KeyError:
            pass

    def check_authorized(
        self, method: str, url: str, data: Optional[Dict[Any, Any]] = {}
    ) -> Any:
        try:
            r = getattr(self.client, method)(url, data, format="json")
            self.assertNotEqual(r.status_code, 403)
            return r
        except KeyError:
            pass

    def check_authorized_superuser(
        self, method: str, url: str, data: Optional[Dict[Any, Any]] = {}
    ) -> Any:
        try:
            # create django superuser and test authorized
            user = baker.make("accounts.User", is_active=True, is_superuser=True)
            self.client.force_authenticate(user=user)
            r = getattr(self.client, method)(url, data, format="json")

            self.assertNotEqual(r.status_code, 403)

            # test role superuser
            user = self.create_user_with_roles(["is_superuser"])
            self.client.force_authenticate(user=user)
            r = getattr(self.client, method)(url, data, format="json")

            self.assertNotEqual(r.status_code, 403)
            self.client.logout()
            return r

        # bypasses any data issues in the view since we just want to see if user is authorized
        except KeyError:
            pass

    def create_user_with_roles(self, roles: List[str]) -> User:
        new_role = baker.make("accounts.Role")
        for role in roles:
            setattr(new_role, role, True)

        new_role.save()
        return baker.make("accounts.User", role=new_role, is_active=True)

    def setup_base_instance(self):
        self.company1: "Client" = baker.make("clients.Client")
        self.company2: "Client" = baker.make("clients.Client")
        self.site1: "Site" = baker.make("clients.Site", client=self.company1)
        self.site2: "Site" = baker.make("clients.Site", client=self.company1)
        self.site3: "Site" = baker.make("clients.Site", client=self.company2)
        self.client_customfield: "CustomField" = baker.make(
            "core.CustomField",
            model=CustomFieldModel.CLIENT,
            type=CustomFieldType.TEXT,
            name="clientCustomField",
        )
        self.site_customfield: "CustomField" = baker.make(
            "core.CustomField",
            model=CustomFieldModel.SITE,
            type=CustomFieldType.TEXT,
            name="siteCustomField",
        )
        self.agent_customfield: "CustomField" = baker.make(
            "core.CustomField",
            model=CustomFieldModel.AGENT,
            type=CustomFieldType.TEXT,
            name="agentCustomField",
        )
