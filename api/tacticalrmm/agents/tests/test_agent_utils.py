from unittest.mock import patch

from django.conf import settings

from agents.utils import generate_linux_install, get_agent_url
from tacticalrmm.test import TacticalTestCase


class TestAgentUtils(TacticalTestCase):
    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.setup_base_instance()

    def test_get_agent_url(self):
        ver = settings.LATEST_AGENT_VER

        # test without token
        r = get_agent_url(goarch="amd64", plat="windows", token="")
        expected = f"https://github.com/amidaware/rmmagent/releases/download/v{ver}/tacticalagent-v{ver}-windows-amd64.exe"
        self.assertEqual(r, expected)

        # test with token
        r = get_agent_url(goarch="386", plat="linux", token="token123")
        expected = f"https://{settings.AGENTS_URL}version={ver}&arch=386&token=token123&plat=linux&api=api.example.com"

    @patch("agents.utils.get_mesh_device_id")
    @patch("agents.utils.asyncio.run")
    @patch("agents.utils.get_mesh_ws_url")
    @patch("agents.utils.get_core_settings")
    def test_generate_linux_install(
        self, mock_core, mock_mesh, mock_async_run, mock_mesh_device_id
    ):
        mock_mesh_device_id.return_value = "meshdeviceid"
        mock_core.return_value.mesh_site = "meshsite"
        mock_async_run.return_value = "meshid"
        mock_mesh.return_value = "meshws"
        r = generate_linux_install(
            client="1",
            site="1",
            agent_type="server",
            arch="amd64",
            token="token123",
            api="api.example.com",
            download_url="asdasd3423",
        )

        ret = r.getvalue().decode("utf-8")

        self.assertIn(r"agentDL='asdasd3423'", ret)
        self.assertIn(
            r"meshDL='meshsite/meshagents?id=meshid&installflags=2&meshinstall=6'", ret
        )
        self.assertIn(r"apiURL='api.example.com'", ret)
        self.assertIn(r"agentDL='asdasd3423'", ret)
        self.assertIn(r"token='token123'", ret)
        self.assertIn(r"clientID='1'", ret)
        self.assertIn(r"siteID='1'", ret)
        self.assertIn(r"agentType='server'", ret)
