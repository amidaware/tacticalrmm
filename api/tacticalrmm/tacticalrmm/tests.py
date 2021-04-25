import json
import os
from unittest.mock import mock_open, patch

import requests
from django.conf import settings
from django.test import TestCase, override_settings

from .utils import (
    bitdays_to_string,
    filter_software,
    generate_winagent_exe,
    get_bit_days,
    reload_nats,
    run_nats_api_cmd,
)


class TestUtils(TestCase):
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

    @override_settings(
        CERT_FILE="/tmp/asdasd.pem",
        KEY_FILE="/tmp/asds55r.pem",
        ALLOWED_HOSTS=["api.example.com"],
        SECRET_KEY="sekret",
        DOCKER_BUILD=True,
    )
    @patch("subprocess.run")
    def test_reload_nats_docker(self, mock_subprocess):
        _ = reload_nats()

        mock_subprocess.assert_not_called()

    @override_settings(
        ALLOWED_HOSTS=["api.example.com"], SECRET_KEY="sekret", DOCKER_BUILD=False
    )
    @patch("subprocess.run")
    def test_reload_nats(self, mock_subprocess):
        _ = reload_nats()

        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_run_nats_api_cmd(self, mock_subprocess):
        ids = ["a", "b", "c"]
        _ = run_nats_api_cmd("monitor", ids)
        mock_subprocess.assert_called_once()

    def test_bitdays_to_string(self):
        a = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        all_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        bit_weekdays = get_bit_days(a)
        r = bitdays_to_string(bit_weekdays)
        self.assertEqual(r, ", ".join(a))

        bit_weekdays = get_bit_days(all_days)
        r = bitdays_to_string(bit_weekdays)
        self.assertEqual(r, "Every day")

    def test_filter_software(self):
        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/software1.json")
        ) as f:
            sw = json.load(f)

        r = filter_software(sw)
        self.assertIsInstance(r, list)
