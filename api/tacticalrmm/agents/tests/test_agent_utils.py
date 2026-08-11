import pickle
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from agents.utils import (
    generate_linux_install,
    get_agent_url,
    strip_relation_caches_for_cache,
)
from automation.models import Policy
from checks.models import Check
from scripts.models import Script
from tacticalrmm.test import TacticalTestCase


class TestStripRelationCaches(SimpleTestCase):
    def test_returns_isolated_copy_with_only_required_relations(self):
        policy = Policy(pk=1)
        script = Script(pk=2)
        check = Check(pk=3, policy=policy, script=script)
        check._prefetched_objects_cache = {"assignedtasks": [object()]}
        check.check_result = object()

        cleaned = strip_relation_caches_for_cache([check])[0]

        self.assertIsNot(cleaned, check)
        self.assertIsNot(cleaned._state, check._state)
        self.assertEqual(cleaned.policy_id, policy.pk)
        self.assertEqual(cleaned.script_id, script.pk)
        self.assertEqual(cleaned._state.fields_cache, {"script": script})
        self.assertEqual(cleaned._prefetched_objects_cache, {})
        self.assertNotIn("check_result", cleaned.__dict__)

        restored = pickle.loads(pickle.dumps(cleaned))
        self.assertEqual(restored.pk, check.pk)
        self.assertEqual(restored.policy_id, policy.pk)
        self.assertEqual(restored.script, script)

        # should not modify instances that callers may still use
        self.assertEqual(check._state.fields_cache["policy"], policy)
        self.assertEqual(check._state.fields_cache["script"], script)
        self.assertIn("assignedtasks", check._prefetched_objects_cache)
        self.assertIn("check_result", check.__dict__)


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
