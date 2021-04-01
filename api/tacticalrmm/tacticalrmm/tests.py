from unittest.mock import mock_open, patch

import requests

from .test import TacticalTestCase
from .utils import generate_winagent_exe


class TestUtils(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("requests.post")
    @patch("__main__.__builtins__.open", new_callable=mock_open)
    def test_generate_winagent_exe_success(self, m_open, mock_post):
        r = generate_winagent_exe(
            client=1,
            site=1,
            agent_type="server",
            rdp=1,
            ping=0,
            power=0,
            arch="64",
            token="abc123",
            api="https://api.example.com",
            file_name="rmm-client-site-server.exe",
        )
        self.assertEqual(r.status_code, 200)

    @patch("requests.post")
    def test_generate_winagent_exe_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()

        r = generate_winagent_exe(
            client=1,
            site=1,
            agent_type="server",
            rdp=1,
            ping=0,
            power=0,
            arch="64",
            token="abc123",
            api="https://api.example.com",
            file_name="rmm-client-site-server.exe",
        )
        self.assertEqual(r.status_code, 400)
