import json
import os
from unittest.mock import patch

from django.conf import settings
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import ChocoSoftware
from .serializers import InstalledSoftwareSerializer

base_url = "/software"


class TestSoftwareViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_chocos_get(self):
        url = f"{base_url}/chocos/"
        with open(os.path.join(settings.BASE_DIR, "software/chocos.json")) as f:
            chocos = json.load(f)

        if ChocoSoftware.objects.exists():
            ChocoSoftware.objects.all().delete()

        ChocoSoftware(chocos=chocos).save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.check_not_authenticated("get", url)

    def test_get_installed_software(self):
        # test a call where agent doesn't exist
        resp = self.client.get("/software/dytthgc/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"{base_url}/{agent.agent_id}/"

        # test without agent software
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

        # make some software
        software = baker.make(
            "software.InstalledSoftware",
            agent=agent,
            software={},
        )

        serializer = InstalledSoftwareSerializer(software)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # test checking all software (multiple agents)
        serializer = InstalledSoftwareSerializer([software], many=True)
        resp = self.client.get(f"{base_url}/", format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_install_softare(self, nats_cmd):
        # test agent doesn't exist
        r = self.client.post(f"{base_url}/kjh34kj5hj45hj4/", format="json")
        self.assertEqual(r.status_code, 404)

        # test old agent version
        old_agent = baker.make_recipe("agents.online_agent", version="1.4.7")
        url = f"{base_url}/{old_agent.agent_id}/"

        data = {
            "pk": old_agent.pk,
            "name": "duplicati",
        }

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        agent = baker.make_recipe(
            "agents.online_agent", version=settings.LATEST_AGENT_VER
        )
        url = f"{base_url}/{agent.agent_id}/"
        data = {
            "pk": agent.pk,
            "name": "duplicati",
        }
        nats_cmd.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        nats_cmd.reset_mock()
        nats_cmd.return_value = "ok"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_refresh_installed_software(self, nats_cmd):
        url = f"{base_url}/76fytfuytff66565f65/"
        r = self.client.put(url, format="json")
        self.assertEqual(r.status_code, 404)

        nats_cmd.return_value = "timeout"
        agent = baker.make_recipe("agents.agent")
        baker.make(
            "software.InstalledSoftware",
            agent=agent,
            software={},
        )
        url = f"{base_url}/{agent.agent_id}/"
        r = self.client.put(url, format="json")
        self.assertEqual(r.status_code, 400)

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/software1.json")
        ) as f:
            sw = json.load(f)

        nats_cmd.reset_mock()
        nats_cmd.return_value = sw
        r = self.client.put(url, format="json")
        self.assertEqual(r.status_code, 200)

        s = agent.installedsoftware_set.first()
        s.delete()
        r = self.client.put(url, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("put", url)


class TestSoftwarePermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()

    def test_list_software_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        software = baker.make("software.InstalledSoftware", software={}, agent=agent)
        unauthorized_software = baker.make(  # noqa
            "software.InstalledSoftware", software={}, agent=unauthorized_agent
        )

        # test super user access
        self.check_authorized_superuser("get", f"{base_url}/")
        self.check_authorized_superuser("get", f"{base_url}/{agent.agent_id}/")

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        self.check_not_authorized("get", f"{base_url}/")
        self.check_not_authorized("get", f"{base_url}/{agent.agent_id}/")

        # add list software role to user
        user.role.can_list_software = True
        user.role.save()

        r = self.check_authorized("get", f"{base_url}/")
        self.assertEqual(len(r.data), 2)
        self.check_authorized("get", f"{base_url}/{agent.agent_id}/")

        # test limiting to client
        user.role.can_view_clients.set([software.agent.client])
        self.check_not_authorized("get", f"{base_url}/{unauthorized_agent.agent_id}/")
        self.check_authorized("get", f"{base_url}/{agent.agent_id}/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/")
        self.assertEqual(len(r.data), 1)

    @patch("agents.models.Agent.nats_cmd")
    def test_install_refresh_software_permissions(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        software = baker.make(  # noqa
            "software.InstalledSoftware", software={}, agent=agent
        )
        unauthorized_software = baker.make(  # noqa
            "software.InstalledSoftware", software={}, agent=unauthorized_agent
        )

        for method in ["post", "put"]:
            if method == "post":
                nats_cmd.return_value = "ok"
            else:
                nats_cmd.return_value = []

            # test superuser access
            self.check_authorized_superuser(method, f"{base_url}/{agent.agent_id}/")
            self.check_authorized_superuser(
                method, f"{base_url}/{unauthorized_agent.agent_id}/"
            )

            # test user with no roles
            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

            self.check_not_authorized(method, f"{base_url}/{agent.agent_id}/")
            self.check_not_authorized(
                method, f"{base_url}/{unauthorized_agent.agent_id}/"
            )

            # add manage software role
            user.role.can_manage_software = True
            user.role.save()

            self.check_authorized(method, f"{base_url}/{agent.agent_id}/")
            self.check_authorized(method, f"{base_url}/{unauthorized_agent.agent_id}/")

            # limit to specific site
            user.role.can_view_sites.set([agent.site])

            self.check_authorized(method, f"{base_url}/{agent.agent_id}/")
            self.check_not_authorized(
                method, f"{base_url}/{unauthorized_agent.agent_id}/"
            )
