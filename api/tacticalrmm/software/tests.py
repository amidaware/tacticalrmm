from tacticalrmm.test import TacticalTestCase
from .serializers import InstalledSoftwareSerializer
from model_bakery import baker
from unittest.mock import patch
from .models import InstalledSoftware, ChocoLog
from agents.models import Agent


class TestSoftwareViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()

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

    @patch("agents.models.Agent.salt_api_cmd")
    def test_chocos_refresh(self, salt_api_cmd):

        salt_return = {"git": "2.3.4", "docker": "1.0.2"}

        # test a call where agent doesn't exist
        resp = self.client.get("/software/refresh/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"/software/refresh/{agent.pk}/"

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        salt_api_cmd.reset_mock()

        salt_api_cmd.return_value = "error"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        salt_api_cmd.reset_mock()

        # test success and created new software object
        salt_api_cmd.return_value = salt_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        self.assertTrue(InstalledSoftware.objects.filter(agent=agent).exists())
        salt_api_cmd.reset_mock()

        # test success and updates software object
        salt_api_cmd.return_value = salt_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        software = agent.installedsoftware_set.get()

        expected = [
            {"name": "git", "version": "2.3.4"},
            {"name": "docker", "version": "1.0.2"},
        ]

        self.assertTrue(InstalledSoftware.objects.filter(agent=agent).exists())
        self.assertEquals(software.software, expected)

        self.check_not_authenticated("get", url)


class TestSoftwareTasks(TacticalTestCase):
    @patch("agents.models.Agent.salt_api_cmd")
    def test_install_chocolatey(self, salt_api_cmd):
        from .tasks import install_chocolatey

        agent = baker.make_recipe("agents.agent")

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        ret = install_chocolatey(agent.pk)

        salt_api_cmd.assert_called_with(
            timeout=120, func="chocolatey.bootstrap", arg="force=True"
        )
        self.assertFalse(ret)

        # test successful
        salt_api_cmd.return_value = "chocolatey is now ready"
        ret = install_chocolatey(agent.pk)

        salt_api_cmd.assert_called_with(
            timeout=120, func="chocolatey.bootstrap", arg="force=True"
        )
        self.assertTrue(ret)
        self.assertTrue(Agent.objects.get(pk=agent.pk).choco_installed)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_update_chocos(self, salt_api_cmd):
        from .tasks import update_chocos

        # initialize data
        online_agent = baker.make_recipe("agents.online_agent", choco_installed=True)
        baker.make("software.ChocoSoftware", chocos={})

        # return data
        chocolately_list = {
            "git": "2.3.4",
            "docker": "1.0.2",
        }

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        ret = update_chocos()

        salt_api_cmd.assert_called_with(timeout=10, func="test.ping")
        self.assertTrue(ret)
        self.assertEquals(salt_api_cmd.call_count, 1)
        salt_api_cmd.reset_mock()

        # test successful attempt
        salt_api_cmd.side_effect = [True, chocolately_list]
        ret = update_chocos()
        self.assertTrue(ret)
        salt_api_cmd.assert_any_call(timeout=10, func="test.ping")
        salt_api_cmd.assert_any_call(timeout=200, func="chocolatey.list")
        self.assertEquals(salt_api_cmd.call_count, 2)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_get_installed_software(self, salt_api_cmd):
        from .tasks import get_installed_software

        agent = baker.make_recipe("agents.agent")

        salt_return = {"git": "2.3.4", "docker": "1.0.2"}

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        ret = get_installed_software(agent.pk)
        self.assertFalse(ret)
        salt_api_cmd.assert_called_with(
            timeout=30,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        salt_api_cmd.reset_mock()

        # test successful attempt
        salt_api_cmd.return_value = salt_return
        ret = get_installed_software(agent.pk)
        self.assertTrue(ret)
        salt_api_cmd.assert_called_with(
            timeout=30,
            func="pkg.list_pkgs",
            kwargs={"include_components": False, "include_updates": False},
        )
        software = agent.installedsoftware_set.get()

        expected = [
            {"name": "git", "version": "2.3.4"},
            {"name": "docker", "version": "1.0.2"},
        ]

        self.assertTrue(InstalledSoftware.objects.filter(agent=agent).exists())
        self.assertEquals(software.software, expected)

    @patch("agents.models.Agent.salt_api_cmd")
    @patch("software.tasks.get_installed_software.delay")
    def test_install_program(self, get_installed_software, salt_api_cmd):
        from .tasks import install_program

        agent = baker.make_recipe("agents.agent")

        # failed attempt
        salt_api_cmd.return_value = "timeout"
        ret = install_program(agent.pk, "git", "2.3.4")
        self.assertFalse(ret)
        salt_api_cmd.assert_called_with(
            timeout=900, func="chocolatey.install", arg=["git", "version=2.3.4"]
        )
        salt_api_cmd.reset_mock()

        # successfully attempt
        salt_api_cmd.return_value = "install of git was successful"
        ret = install_program(agent.pk, "git", "2.3.4")
        self.assertTrue(ret)
        salt_api_cmd.assert_called_with(
            timeout=900, func="chocolatey.install", arg=["git", "version=2.3.4"]
        )
        get_installed_software.assert_called_with(agent.pk)

        self.assertTrue(ChocoLog.objects.filter(agent=agent, name="git").exists())
