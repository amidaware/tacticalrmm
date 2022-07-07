from unittest.mock import patch

from rest_framework.response import Response

from tacticalrmm.test import TacticalTestCase


class TestAgentInstalls(TacticalTestCase):
    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.setup_base_instance()

    @patch("agents.utils.generate_linux_install")
    @patch("knox.models.AuthToken.objects.create")
    @patch("tacticalrmm.utils.generate_winagent_exe")
    @patch("core.utils.token_is_valid")
    @patch("agents.utils.get_agent_url")
    def test_install_agent(
        self,
        mock_agent_url,
        mock_token_valid,
        mock_gen_win_exe,
        mock_auth,
        mock_linux_install,
    ):
        mock_agent_url.return_value = "https://example.com"
        mock_token_valid.return_value = "", False
        mock_gen_win_exe.return_value = Response("ok")
        mock_auth.return_value = "", "token"
        mock_linux_install.return_value = Response("ok")

        url = "/agents/installer/"

        # test windows dynamic exe
        data = {
            "installMethod": "exe",
            "client": self.site2.client.pk,
            "site": self.site2.pk,
            "expires": 24,
            "agenttype": "server",
            "power": 0,
            "rdp": 1,
            "ping": 0,
            "goarch": "amd64",
            "api": "https://api.example.com",
            "fileName": "rmm-client-site-server.exe",
            "plat": "windows",
        }

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        mock_gen_win_exe.assert_called_with(
            client=self.site2.client.pk,
            site=self.site2.pk,
            agent_type="server",
            rdp=1,
            ping=0,
            power=0,
            goarch="amd64",
            token="token",
            api="https://api.example.com",
            file_name="rmm-client-site-server.exe",
        )

        # test linux no code sign
        data["plat"] = "linux"
        data["installMethod"] = "bash"
        data["rdp"] = 0
        data["agenttype"] = "workstation"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        # test linux
        mock_token_valid.return_value = "token123", True
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        mock_linux_install.assert_called_with(
            client=str(self.site2.client.pk),
            site=str(self.site2.pk),
            agent_type="workstation",
            arch="amd64",
            token="token",
            api="https://api.example.com",
            download_url="https://example.com",
        )

        # test manual
        data["rdp"] = 1
        data["installMethod"] = "manual"
        r = self.client.post(url, data, format="json")
        self.assertIn("rdp", r.json()["cmd"])
        self.assertNotIn("power", r.json()["cmd"])

        data.update({"ping": 1, "power": 1})
        r = self.client.post(url, data, format="json")
        self.assertIn("power", r.json()["cmd"])
        self.assertIn("ping", r.json()["cmd"])

        # test powershell
        data["installMethod"] = "powershell"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)
