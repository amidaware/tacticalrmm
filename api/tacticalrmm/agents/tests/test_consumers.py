import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.consumers import (
    CommandStreamConsumer,
    InvalidTerminalShellError,
    TerminalStreamConsumer,
    active_streams,
)
from agents.models import Agent, AgentHistory, AgentPlat
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from logs.models import AuditLog
from model_bakery import baker
from tacticalrmm.test import TacticalTestCase

User = get_user_model()


class TestCommandStreamConsumer(TacticalTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client_obj = baker.make("clients.Client")
        self.site = baker.make("clients.Site", client=self.client_obj)

        self.agent = baker.make(
            "agents.Agent",
            site=self.site,
            agent_id="agent123",
            hostname="agent-host",
            version="2.10.0",
        )

        self.consumer = CommandStreamConsumer()
        self.consumer.scope = {
            "user": self.user,
            "client": ("127.0.0.1", 12345),
            "url_route": {"kwargs": {"agent_id": self.agent.agent_id}},
        }
        self.consumer.user = self.user
        self.consumer.channel_name = "test_channel"
        self.consumer.agent_id = self.agent.agent_id
        self.consumer.group_name = f"agent_cmd_{self.agent.agent_id}"
        self.consumer.channel_layer = AsyncMock()

    @patch.object(CommandStreamConsumer, "send_json", autospec=True)
    def test_creates_agent_history_and_auditlog(self, mock_send_json):
        self.consumer.authorized = True
        message = {
            "cmd": "ping google.com",
            "shell": "cmd",
            "timeout": 5,
        }
        self.consumer.channel_layer = AsyncMock()
        self.consumer.channel_layer.group_add = AsyncMock()
        self.consumer.channel_layer.group_discard = AsyncMock()

        async_to_sync(self.consumer.receive_json)(message)
        history = AgentHistory.objects.filter(agent=self.agent).last()
        self.assertIsNotNone(history)
        self.assertEqual(history.command, "ping google.com")
        self.assertEqual(history.username, "tester")

        audit = AuditLog.objects.filter(agent_id=self.agent.agent_id).last()
        self.assertIsNotNone(audit)
        self.assertIn("ping google.com", audit.after_value)
        self.assertIn("tester issued cmd command", audit.message)
        mock_send_json.assert_called()

    @patch.object(CommandStreamConsumer, "send_json", autospec=True)
    def test_receive_json_invalid_payload(self, mock_send_json):
        self.consumer.authorized = True
        message = {"shell": "cmd"}  # Missing 'cmd'
        async_to_sync(self.consumer.receive_json)(message)
        mock_send_json.assert_called_with(
            self.consumer, {"error": "Invalid command payload"}
        )

    @patch.object(CommandStreamConsumer, "close", new_callable=AsyncMock)
    def test_connect_unauthorized_user_closes_socket(self, mock_close):
        self.consumer.scope["user"] = AnonymousUser()
        async_to_sync(self.consumer.connect)()
        mock_close.assert_awaited_once()

    def test_disconnect_cleans_up_active_streams(self):
        stop_evt = asyncio.Event()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_future()
        task.set_result(None)
        self.consumer.cmd_id = "testcmd"
        active_streams[self.consumer.channel_name] = {"testcmd": (stop_evt, task)}
        self.consumer.channel_layer = AsyncMock()
        self.consumer.channel_layer.group_discard = AsyncMock()
        async_to_sync(self.consumer.disconnect)(1000)
        self.assertNotIn(self.consumer.channel_name, active_streams)
        self.consumer.channel_layer.group_discard.assert_awaited_once()
        loop.close()

    @patch.object(CommandStreamConsumer, "send_json", autospec=True)
    def test_stream_output_filters_correct_keys(self, mock_send_json):
        event = {
            "cmd_id": "abc123",
            "output": "line",
            "done": True,
            "exit_code": 0,
            "extra": "ignoreme",
        }
        async_to_sync(self.consumer.stream_output)(event)
        mock_send_json.assert_called_with(
            self.consumer,
            {"cmd_id": "abc123", "output": "line", "done": True, "exit_code": 0},
        )

    @patch.object(CommandStreamConsumer, "accept", new_callable=AsyncMock)
    @patch.object(CommandStreamConsumer, "has_perm", return_value=True)
    def test_connect_authorized_user(self, mock_perm, mock_accept):
        self.consumer.channel_layer = AsyncMock()
        self.consumer.channel_layer.group_add = AsyncMock()
        self.consumer.channel_layer.group_discard = AsyncMock()

        async_to_sync(self.consumer.connect)()
        mock_accept.assert_awaited_once()
        self.assertFalse(
            self.consumer.channel_layer.group_add.await_args_list,
            "group_add was unexpectedly awaited during connect()",
        )

    @patch.object(CommandStreamConsumer, "send_json", new_callable=AsyncMock)
    @patch.object(CommandStreamConsumer, "accept", new_callable=AsyncMock)
    @patch.object(CommandStreamConsumer, "close", new_callable=AsyncMock)
    @patch.object(CommandStreamConsumer, "has_perm", return_value=False)
    def test_connect_permission_denied(
        self, mock_perm, mock_close, mock_accept, mock_send_json
    ):
        async_to_sync(self.consumer.connect)()
        mock_accept.assert_awaited_once()
        mock_send_json.assert_awaited_once_with(
            {
                "error": "You do not have permission to perform this action.",
                "status": 403,
            }
        )
        mock_close.assert_awaited_once()

    def test_disconnect_only_cleans_up_its_own_cmd(self):
        stop_evt1 = asyncio.Event()
        stop_evt2 = asyncio.Event()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task1 = loop.create_future()
        task1.set_result(None)
        task2 = loop.create_future()
        task2.set_result(None)

        self.consumer.cmd_id = "cmd1"
        active_streams[self.consumer.channel_name] = {
            "cmd1": (stop_evt1, task1),
            "cmd2": (stop_evt2, task2),
        }

        self.consumer.channel_layer = AsyncMock()
        self.consumer.channel_layer.group_discard = AsyncMock()
        async_to_sync(self.consumer.disconnect)(1000)
        self.assertIn(self.consumer.channel_name, active_streams)
        self.assertNotIn("cmd1", active_streams[self.consumer.channel_name])
        self.assertIn("cmd2", active_streams[self.consumer.channel_name])

        loop.close()


@pytest.mark.django_db
class TestNatsStreamCmd:
    @pytest.fixture
    def agent(db):
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)

        agent = Agent(
            hostname="test-agent",
            agent_id="agent123",
            site=site,
            version="2.10.0",
        )
        agent.save()
        return agent

    # helper used to assert group_send was called either awaited or sync
    def _assert_group_send_called(mock_layer, expected_group, expected_payload):
        """
        Accepts both awaited (AsyncMock) or sync-called (Mock) forms.
        """
        try:
            mock_layer.return_value.group_send.assert_awaited_once_with(
                expected_group, expected_payload
            )
        except AssertionError:
            # fallback to sync-called assertion
            mock_layer.return_value.group_send.assert_called_once_with(
                expected_group, expected_payload
            )

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.nats.connect")
    def test_connect_failure_sends_error(self, mock_connect, mock_layer, agent):
        mock_connect.side_effect = Exception("boom")
        mock_layer.return_value.group_send = AsyncMock()

        async_to_sync(agent.nats_stream_cmd)({"payload": {"cmd_id": "abc"}}, timeout=0)

        # tolerate either awaited or sync call
        try:
            mock_layer.return_value.group_send.assert_awaited_once()
        except AssertionError:
            mock_layer.return_value.group_send.assert_called_once()
        args, _ = mock_layer.return_value.group_send.call_args
        assert args[1]["output"].startswith("[ERROR] Could not connect")

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.msgpack.loads")
    @patch("agents.models.nats.connect")
    def test_message_handler_str_payload(
        self, mock_connect, mock_loads, mock_layer, agent
    ):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        mock_loads.return_value = "hello world"
        mock_layer.return_value.group_send = AsyncMock()

        async def fake_subscribe(subject, cb):
            msg = MagicMock()
            msg.data = b"fake"
            await cb(msg)
            return AsyncMock(unsubscribe=AsyncMock())

        fake_nc.subscribe.side_effect = fake_subscribe

        cmd_id = "abc"
        group = f"agent_cmd_{agent.agent_id}_{cmd_id}"

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": cmd_id}},
            timeout=0,
            group=group,
        )

        mock_layer.return_value.group_send.assert_any_call(
            group,
            {"type": "stream_output", "cmd_id": cmd_id, "output": "hello world"},
        )

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.msgpack.loads")
    @patch("agents.models.nats.connect")
    def test_message_handler_dict_payload(
        self, mock_connect, mock_loads, mock_layer, agent
    ):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        mock_loads.return_value = {"line": "out", "done": True, "exit_code": 5}
        mock_layer.return_value.group_send = AsyncMock()

        async def fake_subscribe(subject, cb):
            msg = MagicMock()
            msg.data = b"fake"
            await cb(msg)
            return AsyncMock(unsubscribe=AsyncMock())

        fake_nc.subscribe.side_effect = fake_subscribe

        cmd_id = "xyz"
        group = f"agent_cmd_{agent.agent_id}_{cmd_id}"

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": cmd_id}},
            timeout=0,
            group=group,
        )

        mock_layer.return_value.group_send.assert_any_call(
            group,
            {
                "type": "stream_output",
                "cmd_id": cmd_id,
                "output": "out",
                "done": True,
                "exit_code": 5,
            },
        )

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.nats.connect")
    def test_stop_event_triggers_early_exit(self, mock_connect, mock_layer, agent):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        fake_nc.subscribe.return_value = AsyncMock(unsubscribe=AsyncMock())
        stop_evt = asyncio.Event()
        stop_evt.set()

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": "early"}}, timeout=5, stop_evt=stop_evt
        )

        fake_nc.close.assert_awaited_once()

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.nats.connect")
    def test_publish_subscribe_failure_sends_error(
        self, mock_connect, mock_layer, agent
    ):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        fake_nc.publish.side_effect = Exception("publish failed")
        mock_layer.return_value.group_send = AsyncMock()

        cmd_id = "oops"
        group = f"agent_cmd_{agent.agent_id}_{cmd_id}"

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": cmd_id}},
            timeout=0,
            group=group,
        )

        mock_layer.return_value.group_send.assert_any_call(
            group,
            {
                "type": "stream_output",
                "cmd_id": cmd_id,
                "output": "[ERROR] NATS publish/subscribe failed: publish failed",
            },
        )

        fake_nc.close.assert_awaited_once()

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.msgpack.loads")
    @patch("agents.models.nats.connect")
    def test_message_handler_payload_decoding_failure(
        self, mock_connect, mock_loads, mock_layer, agent
    ):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        mock_loads.side_effect = Exception("bad data")
        mock_layer.return_value.group_send = AsyncMock()

        async def fake_subscribe(subject, cb):
            msg = MagicMock()
            msg.data = b"corrupt"
            await cb(msg)
            return AsyncMock(unsubscribe=AsyncMock())

        fake_nc.subscribe.side_effect = fake_subscribe

        cmd_id = "err123"
        group = f"agent_cmd_{agent.agent_id}_{cmd_id}"

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": cmd_id}},
            timeout=0,
            group=group,
        )

        mock_layer.return_value.group_send.assert_any_call(
            group,
            {
                "type": "stream_output",
                "cmd_id": cmd_id,
                "output": "[ERROR] bad data",
            },
        )

    @patch("agents.models.get_channel_layer")
    @patch("agents.models.nats.connect")
    def test_timeout_triggers_cleanup(self, mock_connect, mock_layer, agent):
        fake_nc = AsyncMock()
        mock_connect.return_value = fake_nc
        sub = AsyncMock()
        fake_nc.subscribe.return_value = sub
        mock_layer.return_value.group_send = AsyncMock()

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": "to123"}}, timeout=0
        )

        sub.unsubscribe.assert_awaited_once()
        fake_nc.close.assert_awaited_once()


class TestTerminalStreamConsumer(TacticalTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client_obj = baker.make("clients.Client")
        self.site = baker.make("clients.Site", client=self.client_obj)

        self.agent = baker.make(
            "agents.Agent",
            site=self.site,
            agent_id="agent123",
            hostname="agent-host",
            plat=AgentPlat.WINDOWS,
        )

        self.session_id = "11111111-1111-4111-8111-111111111111"

        self.consumer = TerminalStreamConsumer()
        self.consumer.scope = {
            "user": self.user,
            "client": ("127.0.0.1", 12345),
            "url_route": {
                "kwargs": {
                    "agent_id": self.agent.agent_id,
                    "session_id": self.session_id,
                }
            },
        }
        self.consumer.user = self.user
        self.consumer.channel_name = "test_terminal_channel"
        self.consumer.agent_id = self.agent.agent_id
        self.consumer.session_id = self.session_id
        self.consumer.group_name = f"terminal_{self.agent.agent_id}_{self.session_id}"
        self.consumer.channel_layer = AsyncMock()
        self.consumer.channel_layer.group_add = AsyncMock()
        self.consumer.channel_layer.group_discard = AsyncMock()

    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    def test_connect_anonymous_user_closes_socket(self, mock_close):
        self.consumer.scope["user"] = AnonymousUser()

        async_to_sync(self.consumer.connect)()

        mock_close.assert_awaited_once()

    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    def test_connect_unauthenticated_user_closes_with_4401(self, mock_close):
        self.consumer.scope["user"] = SimpleNamespace(
            is_authenticated=False,
            block_dashboard_login=False,
        )

        async_to_sync(self.consumer.connect)()

        mock_close.assert_awaited_once_with(4401)

    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    def test_connect_blocked_dashboard_user_closes_socket(self, mock_close):
        self.user.block_dashboard_login = True
        self.user.save(update_fields=["block_dashboard_login"])

        async_to_sync(self.consumer.connect)()

        mock_close.assert_awaited_once()

    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    def test_connect_invalid_session_id_closes_socket(self, mock_close):
        self.consumer.scope["url_route"]["kwargs"]["session_id"] = "not-a-uuid"

        async_to_sync(self.consumer.connect)()

        mock_close.assert_awaited_once()

    @patch.object(TerminalStreamConsumer, "send_json", new_callable=AsyncMock)
    @patch.object(TerminalStreamConsumer, "accept", new_callable=AsyncMock)
    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    @patch.object(
        TerminalStreamConsumer, "has_perm", new_callable=AsyncMock, return_value=False
    )
    def test_connect_permission_denied(
        self, mock_has_perm, mock_close, mock_accept, mock_send_json
    ):
        async_to_sync(self.consumer.connect)()

        mock_accept.assert_not_awaited()
        mock_send_json.assert_not_awaited()
        mock_close.assert_awaited_once_with(code=4003)
        self.consumer.channel_layer.group_add.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "accept", new_callable=AsyncMock)
    @patch.object(TerminalStreamConsumer, "has_perm", return_value=True)
    def test_connect_authorized_user_adds_group_and_accepts(
        self, mock_has_perm, mock_accept
    ):
        async_to_sync(self.consumer.connect)()

        expected_group = f"terminal_{self.agent.agent_id}_{self.session_id}"
        self.assertEqual(self.consumer.group_name, expected_group)

        self.consumer.channel_layer.group_add.assert_awaited_once_with(
            expected_group,
            self.consumer.channel_name,
        )
        mock_accept.assert_awaited_once()

    @patch.object(TerminalStreamConsumer, "close", new_callable=AsyncMock)
    def test_receive_json_unknown_action_sends_error(self, mock_close):
        self.consumer.send_json = AsyncMock()

        async_to_sync(self.consumer.receive_json)({"action": "unknown_action"})

        self.consumer.send_json.assert_awaited_once_with(
            {"error": "Unknown action: unknown_action"}
        )
        mock_close.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "_send_kill", new_callable=AsyncMock)
    def test_disconnect_cleans_up_group_sub_and_nc(self, mock_send_kill):
        self.consumer.killed = False

        sub = AsyncMock()
        nc = AsyncMock()
        nc.is_closed = False

        self.consumer.sub = sub
        self.consumer.nc = nc

        async_to_sync(self.consumer.disconnect)(1000)

        self.consumer.channel_layer.group_discard.assert_awaited_once_with(
            self.consumer.group_name,
            self.consumer.channel_name,
        )
        mock_send_kill.assert_awaited_once()
        sub.unsubscribe.assert_awaited_once()
        nc.close.assert_awaited_once()
        self.assertIsNone(self.consumer.sub)
        self.assertIsNone(self.consumer.nc)

    @patch.object(TerminalStreamConsumer, "_send_kill", new_callable=AsyncMock)
    def test_disconnect_does_not_send_kill_if_already_killed(self, mock_send_kill):
        self.consumer.killed = True

        sub = AsyncMock()
        nc = AsyncMock()
        nc.is_closed = False

        self.consumer.sub = sub
        self.consumer.nc = nc

        async_to_sync(self.consumer.disconnect)(1000)

        mock_send_kill.assert_not_awaited()
        sub.unsubscribe.assert_awaited_once()
        nc.close.assert_awaited_once()
        self.assertIsNone(self.consumer.sub)
        self.assertIsNone(self.consumer.nc)

    @patch.object(TerminalStreamConsumer, "_start_terminal", new_callable=AsyncMock)
    def test_receive_json_routes_start_action(self, mock_start):
        payload = {"action": "start", "shell": "cmd"}

        async_to_sync(self.consumer.receive_json)(payload)

        mock_start.assert_awaited_once_with(payload)

    @patch.object(TerminalStreamConsumer, "_send_input", new_callable=AsyncMock)
    def test_receive_json_routes_input_action(self, mock_send_input):
        async_to_sync(self.consumer.receive_json)({"action": "input", "data": "dir"})

        mock_send_input.assert_awaited_once_with("dir")

    @patch.object(TerminalStreamConsumer, "_send_resize", new_callable=AsyncMock)
    def test_receive_json_routes_resize_action(self, mock_send_resize):
        async_to_sync(self.consumer.receive_json)(
            {"action": "resize", "rows": 30, "cols": 100}
        )

        mock_send_resize.assert_awaited_once_with(30, 100)

    @patch.object(TerminalStreamConsumer, "_send_kill", new_callable=AsyncMock)
    def test_receive_json_routes_kill_action(self, mock_send_kill):
        self.consumer.killed = False

        async_to_sync(self.consumer.receive_json)({"action": "kill"})

        self.assertTrue(self.consumer.killed)
        mock_send_kill.assert_awaited_once()

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_input_publishes_when_started_and_value_present(self, mock_publish):
        self.consumer.started = True

        async_to_sync(self.consumer._send_input)("ls -la")

        mock_publish.assert_awaited_once_with(
            {
                "func": "terminal_input",
                "payload": {
                    "session_id": self.session_id,
                    "data": "ls -la",
                },
            }
        )

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_input_skips_when_not_started(self, mock_publish):
        self.consumer.started = False

        async_to_sync(self.consumer._send_input)("ls -la")

        mock_publish.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_input_skips_when_value_empty(self, mock_publish):
        self.consumer.started = True

        async_to_sync(self.consumer._send_input)("")

        mock_publish.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_resize_publishes_when_started(self, mock_publish):
        self.consumer.started = True

        async_to_sync(self.consumer._send_resize)(24, 80)

        mock_publish.assert_awaited_once_with(
            {
                "func": "terminal_resize",
                "payload": {
                    "session_id": self.session_id,
                    "rows": "24",
                    "cols": "80",
                },
            }
        )

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_resize_skips_when_not_started(self, mock_publish):
        self.consumer.started = False

        async_to_sync(self.consumer._send_resize)(24, 80)

        mock_publish.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_resize_skips_when_rows_or_cols_missing(self, mock_publish):
        self.consumer.started = True

        async_to_sync(self.consumer._send_resize)(None, 80)
        async_to_sync(self.consumer._send_resize)(24, None)

        mock_publish.assert_not_awaited()

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    def test_send_kill_publishes_expected_payload(self, mock_publish):
        async_to_sync(self.consumer._send_kill)()

        mock_publish.assert_awaited_once_with(
            {
                "func": "terminal_kill",
                "payload": {"session_id": self.session_id},
            }
        )

    def test_resolve_explicit_shell_windows_token(self):
        shell = self.consumer._resolve_explicit_shell("powershell", AgentPlat.WINDOWS)
        self.assertEqual(shell, "powershell")

    def test_resolve_explicit_shell_windows_invalid_raises(self):
        with self.assertRaises(InvalidTerminalShellError):
            self.consumer._resolve_explicit_shell("bash", AgentPlat.WINDOWS)

    def test_resolve_default_shell_windows_falls_back_to_cmd(self):
        shell = self.consumer._resolve_default_shell("", AgentPlat.WINDOWS)
        self.assertEqual(shell, "cmd")

    def test_resolve_default_shell_linux_falls_back_to_bash(self):
        shell = self.consumer._resolve_default_shell("", AgentPlat.LINUX)
        self.assertEqual(shell, "bash")

    def test_resolve_default_shell_darwin_falls_back_to_bash(self):
        shell = self.consumer._resolve_default_shell("", AgentPlat.DARWIN)
        self.assertEqual(shell, "bash")

    @patch.object(TerminalStreamConsumer, "send_json", autospec=True)
    def test_stream_output_sends_expected_payload(self, mock_send_json):
        event = {
            "output": "hello",
            "session_id": self.session_id,
            "exit_code": 0,
            "done": True,
            "messageId": "1",
        }

        async_to_sync(self.consumer.stream_output)(event)

        mock_send_json.assert_called_with(
            self.consumer,
            {
                "action": "trmmcli.output",
                "data": {
                    "output": "hello",
                    "session_id": self.session_id,
                    "exit_code": 0,
                    "done": True,
                    "messageId": "1",
                },
            },
        )

    @patch("agents.consumers.msgpack.dumps", return_value=b"packed")
    def test_nats_publish_failure_resets_connection(self, mock_dumps):
        nc = AsyncMock()
        nc.is_closed = False
        nc.publish.side_effect = Exception("publish failed")
        self.consumer.nc = nc

        with self.assertRaises(Exception):
            async_to_sync(self.consumer._nats_publish)({"func": "x"})

        nc.close.assert_awaited_once()
        self.assertIsNone(self.consumer.nc)

    @patch.object(
        TerminalStreamConsumer, "_send_terminal_error", new_callable=AsyncMock
    )
    @patch.object(TerminalStreamConsumer, "_resolve_explicit_shell")
    def test_start_terminal_invalid_shell_sends_terminal_error(
        self, mock_resolve, mock_send_terminal_error
    ):
        mock_resolve.side_effect = InvalidTerminalShellError("Invalid shell.")
        self.agent.plat = AgentPlat.WINDOWS
        self.agent.save(update_fields=["plat"])

        payload = {"shell": "invalid-shell"}

        async_to_sync(self.consumer._start_terminal)(payload)

        mock_send_terminal_error.assert_awaited_once_with(
            "Invalid shell.",
            code="invalid_shell",
        )
        self.assertFalse(self.consumer.started)

    @patch.object(
        TerminalStreamConsumer, "_send_terminal_error", new_callable=AsyncMock
    )
    @patch.object(TerminalStreamConsumer, "_ensure_nats", new_callable=AsyncMock)
    def test_start_terminal_generic_failure_sends_terminal_start_failed(
        self, mock_ensure_nats, mock_send_terminal_error
    ):
        mock_ensure_nats.side_effect = Exception("boom")

        async_to_sync(self.consumer._start_terminal)({})

        mock_send_terminal_error.assert_awaited_once_with(
            "Failed to start terminal session.",
            code="terminal_start_failed",
        )
        self.assertFalse(self.consumer.started)

    @patch.object(TerminalStreamConsumer, "_nats_publish", new_callable=AsyncMock)
    @patch.object(TerminalStreamConsumer, "_ensure_nats", new_callable=AsyncMock)
    @patch("agents.consumers.msgpack.loads")
    def test_start_terminal_message_handler_forwards_output(
        self, mock_loads, mock_ensure_nats, mock_nats_publish
    ):
        self.consumer.group_name = f"terminal_{self.agent.agent_id}_{self.session_id}"
        self.consumer.channel_layer.group_send = AsyncMock()
        self.consumer.nc = AsyncMock()

        mock_loads.return_value = {
            "output": b"hello",
            "done": False,
            "exit_code": 0,
        }

        async def fake_subscribe(subject, cb):
            msg = MagicMock()
            msg.data = b"packed"
            await cb(msg)
            return AsyncMock(unsubscribe=AsyncMock())

        self.consumer.nc.subscribe.side_effect = fake_subscribe

        async_to_sync(self.consumer._start_terminal)({})

        self.consumer.channel_layer.group_send.assert_awaited_once_with(
            self.consumer.group_name,
            {
                "type": "stream_output",
                "session_id": self.session_id,
                "output": "hello",
                "exit_code": 0,
                "messageId": "1",
            },
        )
        mock_nats_publish.assert_awaited_once_with(
            {
                "func": "terminal_start",
                "payload": {
                    "session_id": self.session_id,
                    "shell": "cmd",
                },
                "run_as_user": False,
            }
        )
