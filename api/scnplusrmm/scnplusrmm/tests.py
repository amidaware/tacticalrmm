from unittest.mock import mock_open, patch

import requests
from django.test import override_settings

from checks.constants import CHECK_DEFER, CHECK_RESULT_DEFER
from tacticalrmm.constants import (
    AGENT_DEFER,
    CHECKS_NON_EDITABLE_FIELDS,
    FIELDS_TRIGGER_TASK_UPDATE_AGENT,
    ONLINE_AGENTS,
    POLICY_CHECK_FIELDS_TO_COPY,
    POLICY_TASK_FIELDS_TO_COPY,
)
from tacticalrmm.test import TacticalTestCase

from .utils import bitdays_to_string, generate_winagent_exe, get_bit_days, reload_nats


class TestUtils(TacticalTestCase):
    def setUp(self):
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
            goarch="amd64",
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
            goarch="amd64",
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

    # for checking when removing db fields, make sure we update these tuples
    def test_constants_fields_exist(self) -> None:
        from agents.models import Agent
        from autotasks.models import AutomatedTask
        from checks.models import Check, CheckResult

        agent_fields = [i.name for i in Agent._meta.get_fields()]
        agent_fields.append("pk")

        autotask_fields = [i.name for i in AutomatedTask._meta.get_fields()]
        check_fields = [i.name for i in Check._meta.get_fields()]
        check_result_fields = [i.name for i in CheckResult._meta.get_fields()]

        for i in AGENT_DEFER:
            self.assertIn(i, agent_fields)

        for i in ONLINE_AGENTS:
            self.assertIn(i, agent_fields)

        for i in FIELDS_TRIGGER_TASK_UPDATE_AGENT:
            self.assertIn(i, autotask_fields)

        for i in POLICY_TASK_FIELDS_TO_COPY:
            self.assertIn(i, autotask_fields)

        for i in CHECKS_NON_EDITABLE_FIELDS:
            self.assertIn(i, check_fields)

        for i in POLICY_CHECK_FIELDS_TO_COPY:
            self.assertIn(i, check_fields)

        for i in CHECK_DEFER:
            self.assertIn(i, check_fields)

        for i in CHECK_RESULT_DEFER:
            self.assertIn(i, check_result_fields)
