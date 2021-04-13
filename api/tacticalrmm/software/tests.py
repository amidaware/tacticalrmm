import json
import os
from unittest.mock import patch

from django.conf import settings
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import ChocoSoftware
from .serializers import InstalledSoftwareSerializer


class TestSoftwareViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_chocos_get(self):
        url = "/software/chocos/"
        with open(os.path.join(settings.BASE_DIR, "software/chocos.json")) as f:
            chocos = json.load(f)

        if ChocoSoftware.objects.exists():
            ChocoSoftware.objects.all().delete()

        ChocoSoftware(chocos=chocos).save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.check_not_authenticated("get", url)

    def test_chocos_installed(self):
        # test a call where agent doesn't exist
        resp = self.client.get("/software/installed/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"/software/installed/{agent.pk}/"

        # test without agent software
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.data, [])  # type: ignore

        # make some software
        software = baker.make(
            "software.InstalledSoftware",
            agent=agent,
            software={},
        )

        serializer = InstalledSoftwareSerializer(software)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_install(self, nats_cmd):
        url = "/software/install/"
        old_agent = baker.make_recipe("agents.online_agent", version="1.4.7")
        data = {
            "pk": old_agent.pk,
            "name": "duplicati",
        }

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        agent = baker.make_recipe(
            "agents.online_agent", version=settings.LATEST_AGENT_VER
        )
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
    def test_refresh_installed(self, nats_cmd):
        url = "/software/refresh/4827342/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 404)

        nats_cmd.return_value = "timeout"
        agent = baker.make_recipe("agents.agent")
        baker.make(
            "software.InstalledSoftware",
            agent=agent,
            software={},
        )
        url = f"/software/refresh/{agent.pk}/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 400)

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/software1.json")
        ) as f:
            sw = json.load(f)

        nats_cmd.reset_mock()
        nats_cmd.return_value = sw
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)

        s = agent.installedsoftware_set.first()
        s.delete()
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)
