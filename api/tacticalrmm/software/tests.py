import json
import os

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
        self.assertEquals(resp.data, [])

        # make some software
        software = baker.make(
            "software.InstalledSoftware",
            agent=agent,
            software={},
        )

        serializer = InstalledSoftwareSerializer(software)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.data, serializer.data)

        self.check_not_authenticated("get", url)
