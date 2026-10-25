import pickle
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.conf import settings
from django.test import SimpleTestCase

from agents.utils import (
    collect_file_transfer_paths,
    canonical_file_browser_path,
    generate_linux_install,
    get_agent_url,
    is_posix_abs_path,
    is_windows_path,
    send_nats_command,
    send_nats_notification,
    strip_relation_caches_for_cache,
    validate_file_browser_path,
    validate_file_transfer_destination_path,
    validate_file_transfer_filename,
    validate_file_transfer_source_path,
    normalize_file_browser_path,
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


class TestFileTransferPathValidation(SimpleTestCase):
    """Transfer paths must match listing: apostrophe/ampersand/etc are valid names."""

    def test_transfer_allows_shell_meta_chars_in_paths(self) -> None:
        windows_dir = r"C:\Users\John's Docs"
        windows_file = r"C:\Users\John's Docs\it's & co.txt"
        posix_dir = "/tmp/it's & co"
        posix_file = "/tmp/it's & co/x.txt;done"

        self.assertIsNone(
            validate_file_transfer_destination_path(windows_dir, "windows")
        )
        self.assertIsNone(
            validate_file_transfer_destination_path(windows_file, "windows")
        )
        self.assertIsNone(validate_file_transfer_source_path(windows_file, "windows"))
        self.assertIsNone(validate_file_browser_path(windows_dir, "windows"))

        self.assertIsNone(validate_file_transfer_destination_path(posix_dir, "linux"))
        self.assertIsNone(validate_file_transfer_source_path(posix_file, "linux"))
        self.assertIsNone(validate_file_browser_path(posix_dir, "linux"))
        self.assertIsNone(validate_file_transfer_filename("it's & co.txt"))
        self.assertIsNotNone(validate_file_transfer_filename("trail."))
        self.assertIn(
            "period",
            validate_file_transfer_filename("trail.") or "",
        )
        self.assertIsNone(
            validate_file_transfer_filename(
                "trail.", ban_trailing_space_or_period=False
            )
        )

        paths, err = collect_file_transfer_paths(
            [posix_file, '/tmp/quote"file.txt'], "linux"
        )
        self.assertIsNone(err)
        self.assertEqual(len(paths), 2)

        paths, err = collect_file_transfer_paths(
            [r"C:\Users\John's Docs", r"C:\Users\a|b"], "windows"
        )
        self.assertIsNone(err)
        self.assertEqual(len(paths), 2)

    def test_transfer_still_rejects_control_traversal_and_relative(self) -> None:
        self.assertIsNotNone(
            validate_file_transfer_destination_path("Public", "windows")
        )
        self.assertIsNotNone(validate_file_transfer_source_path("readme.txt", "linux"))
        self.assertIsNotNone(
            validate_file_transfer_destination_path(r"C:\Users\..\Windows", "windows")
        )
        self.assertIsNotNone(
            validate_file_transfer_source_path("/tmp/foo\nbar", "linux")
        )
        self.assertIsNotNone(
            validate_file_transfer_destination_path("/tmp/foo\x00bar", "linux")
        )

    def test_posix_backslash_is_not_a_separator(self) -> None:
        linux_file = r"/tmp/a\b"
        self.assertEqual(normalize_file_browser_path(linux_file, "linux"), linux_file)
        self.assertIsNone(validate_file_browser_path(linux_file, "linux"))
        self.assertIsNone(validate_file_transfer_source_path(linux_file, "linux"))
        self.assertEqual(
            normalize_file_browser_path(r"C:/Users/Public", "windows"),
            r"C:\Users\Public",
        )

    def test_posix_backslash_dotdot_is_not_traversal(self) -> None:
        self.assertIsNone(validate_file_browser_path(r"/tmp/foo\../bar", "linux"))
        self.assertIsNotNone(validate_file_browser_path("/tmp/../etc", "linux"))

    def test_canonical_file_browser_path_matches_agent(self) -> None:
        path, err = canonical_file_browser_path("C:", "windows")
        self.assertIsNone(err)
        self.assertEqual(path, "C:\\")

        path, err = canonical_file_browser_path("C:/Users/Public", "windows")
        self.assertIsNone(err)
        self.assertEqual(path, r"C:\Users\Public")

        path, err = canonical_file_browser_path("/tmp/foo/", "linux")
        self.assertIsNone(err)
        self.assertEqual(path, "/tmp/foo")

        path, err = canonical_file_browser_path(r"/tmp/a\b", "linux")
        self.assertIsNone(err)
        self.assertEqual(path, r"/tmp/a\b")

    def test_shell_helpers_still_ban_metas(self) -> None:
        """Custom shell fields still must not contain injection characters."""
        self.assertFalse(is_posix_abs_path("/bin/bash;id"))
        self.assertFalse(is_posix_abs_path("/tmp/it's"))
        self.assertTrue(is_posix_abs_path("/bin/bash"))
        self.assertFalse(is_windows_path(r"C:\Program Files\it's.exe"))
        self.assertTrue(is_windows_path(r"C:\Windows\System32\cmd.exe"))


class TestSendNatsHelpers(SimpleTestCase):
    def _future(self, result):
        future = MagicMock()
        future.result.return_value = result
        return future

    @patch("agents.utils.asyncio.run_coroutine_threadsafe")
    @patch("agents.utils._ensure_nats_notify_loop")
    def test_send_nats_notification_natsdown_is_error(
        self, _loop, mock_threadsafe
    ) -> None:
        """Connect failure is a string return, not an exception, must not look like success."""
        mock_threadsafe.return_value = self._future("natsdown")
        result = send_nats_notification(MagicMock(), "files_upload_chunk_available", {})
        self.assertEqual(result.status_code, 400)
        self.assertIn("Unable to contact the agent", result.data)

    @patch("agents.utils.asyncio.run_coroutine_threadsafe")
    @patch("agents.utils._ensure_nats_notify_loop")
    def test_send_nats_notification_timeout_is_error(
        self, _loop, mock_threadsafe
    ) -> None:
        mock_threadsafe.return_value = self._future("timeout")
        result = send_nats_notification(MagicMock(), "files_download_ack", {})
        self.assertEqual(result.status_code, 400)
        self.assertIn("Unable to contact the agent", result.data)

    @patch("agents.utils.asyncio.run_coroutine_threadsafe")
    @patch("agents.utils._ensure_nats_notify_loop")
    def test_send_nats_notification_success_returns_none(
        self, _loop, mock_threadsafe
    ) -> None:
        mock_threadsafe.return_value = self._future(None)
        result = send_nats_notification(MagicMock(), "files_upload_chunk_available", {})
        self.assertIsNone(result)

    @patch("agents.utils.asyncio.run")
    def test_send_nats_command_natsdown_is_error(self, mock_run) -> None:
        mock_run.return_value = "natsdown"
        result = send_nats_command(MagicMock(), "files_list", {"path": "/"})
        self.assertEqual(result.status_code, 400)
        self.assertIn("Unable to contact the agent", result.data)

    @patch("agents.utils.asyncio.run")
    def test_send_nats_command_timeout_is_error(self, mock_run) -> None:
        mock_run.return_value = "timeout"
        result = send_nats_command(MagicMock(), "files_list", {"path": "/"})
        self.assertEqual(result.status_code, 400)
        self.assertIn("Unable to contact the agent", result.data)


class TestFileTransferAckKeys(SimpleTestCase):
    @patch("agents.file_transfer_relay._redis_client")
    def test_signal_upload_ack_sets_scalar_only(self, mock_redis_client) -> None:
        client = MagicMock()
        mock_redis_client.return_value = client
        from agents.file_transfer_relay import signal_upload_ack
        from tacticalrmm.constants import FILE_TRANSFER_REDIS_ACK_TTL_SECONDS

        session_id = uuid4()
        signal_upload_ack(session_id, 8192)
        client.set.assert_called_once_with(
            f"upload:ack:{session_id}",
            b"8192",
            ex=FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
        )
        client.pipeline.assert_not_called()
        client.lpush.assert_not_called()

    @patch("agents.file_transfer_relay._redis_client")
    def test_signal_download_ack_sets_scalar_only(self, mock_redis_client) -> None:
        client = MagicMock()
        mock_redis_client.return_value = client
        from agents.file_transfer_relay import signal_download_ack
        from tacticalrmm.constants import FILE_TRANSFER_REDIS_ACK_TTL_SECONDS

        session_id = uuid4()
        signal_download_ack(session_id, 4096)
        client.set.assert_called_once_with(
            f"download:ack:{session_id}",
            b"4096",
            ex=FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
        )
        client.pipeline.assert_not_called()
        client.lpush.assert_not_called()

    @patch("agents.file_transfer_relay._redis_client")
    def test_clear_upload_does_not_scan_ack_events(self, mock_redis_client) -> None:
        client = MagicMock()
        client.scan_iter.return_value = []
        mock_redis_client.return_value = client
        from agents.file_transfer_relay import clear_upload_session_redis

        session_id = uuid4()
        clear_upload_session_redis(session_id)
        patterns = [call.kwargs["match"] for call in client.scan_iter.call_args_list]
        self.assertEqual(patterns, [f"upload:chunk:{session_id}/*"])
        self.assertFalse(any("ack_event" in pattern for pattern in patterns))

    @patch("agents.file_transfer_relay._redis_client")
    def test_clear_download_does_not_scan_event_lists(self, mock_redis_client) -> None:
        client = MagicMock()
        client.scan_iter.return_value = []
        mock_redis_client.return_value = client
        from agents.file_transfer_relay import clear_download_session_redis

        session_id = uuid4()
        clear_download_session_redis(session_id)
        patterns = [call.kwargs["match"] for call in client.scan_iter.call_args_list]
        self.assertEqual(patterns, [f"download:chunk:{session_id}/*"])
        self.assertFalse(
            any(
                "ack_event" in pattern or "chunk_event" in pattern
                for pattern in patterns
            )
        )
