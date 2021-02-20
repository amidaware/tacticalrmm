from unittest.mock import patch

from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import ChocoLog
from .serializers import InstalledSoftwareSerializer


class TestSoftwareViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_chocos_get(self):
        url = "/software/chocos/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.check_not_authenticated("get", url)

    @patch("software.tasks.install_program.delay")
    def test_chocos_install(self, install_program):
        url = "/software/install/"
        agent = baker.make_recipe("agents.agent")

        # test a call where agent doesn't exist
        invalid_data = {"pk": 500, "name": "Test Software", "version": "1.0.0"}
        resp = self.client.post(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        data = {"pk": agent.pk, "name": "Test Software", "version": "1.0.0"}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        install_program.assert_called_with(data["pk"], data["name"], data["version"])

        self.check_not_authenticated("post", url)

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


class TestSoftwareTasks(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_install_program(self, nats_cmd):
        from .tasks import install_program

        agent = baker.make_recipe("agents.agent")
        nats_cmd.return_value = "install of git was successful"
        _ = install_program(agent.pk, "git", "2.3.4")
        nats_cmd.assert_called_with(
            {
                "func": "installwithchoco",
                "choco_prog_name": "git",
                "choco_prog_ver": "2.3.4",
            },
            timeout=915,
        )

        self.assertTrue(ChocoLog.objects.filter(agent=agent, name="git").exists())
