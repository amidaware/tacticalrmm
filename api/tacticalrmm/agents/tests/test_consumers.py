from unittest.mock import patch
from asgiref.sync import async_to_sync
from model_bakery import baker
from django.contrib.auth import get_user_model
from tacticalrmm.test import TacticalTestCase
from agents.models import AgentHistory
from logs.models import AuditLog
from agents.consumers import CommandStreamConsumer, active_streams
from django.contrib.auth.models import AnonymousUser
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from agents.models import Agent

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
        # connect() shouldn't create a per-cmd group; it's done in receive_json()
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
    def agent(self):
        return Agent(agent_id="agent123", hostname="test-agent")

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

        async_to_sync(agent.nats_stream_cmd)({"payload": {"cmd_id": "abc"}}, timeout=0)

        # tolerate either awaited or sync call
        try:
            mock_layer.return_value.group_send.assert_any_await(
                "agent_cmd_agent123",
                {"type": "stream_output", "cmd_id": "abc", "output": "hello world"},
            )
        except AssertionError:
            mock_layer.return_value.group_send.assert_any_call(
                "agent_cmd_agent123",
                {"type": "stream_output", "cmd_id": "abc", "output": "hello world"},
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

        async_to_sync(agent.nats_stream_cmd)({"payload": {"cmd_id": "xyz"}}, timeout=0)

        try:
            mock_layer.return_value.group_send.assert_any_await(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "xyz",
                    "output": "out",
                    "done": True,
                    "exit_code": 5,
                },
            )
        except AssertionError:
            mock_layer.return_value.group_send.assert_any_call(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "xyz",
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

        async_to_sync(agent.nats_stream_cmd)({"payload": {"cmd_id": "oops"}}, timeout=0)

        try:
            mock_layer.return_value.group_send.assert_any_await(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "oops",
                    "output": "[ERROR] NATS publish/subscribe failed: publish failed",
                },
            )
        except AssertionError:
            mock_layer.return_value.group_send.assert_any_call(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "oops",
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

        async_to_sync(agent.nats_stream_cmd)(
            {"payload": {"cmd_id": "err123"}}, timeout=0
        )

        try:
            mock_layer.return_value.group_send.assert_any_await(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "err123",
                    "output": "[ERROR] bad data",
                },
            )
        except AssertionError:
            mock_layer.return_value.group_send.assert_any_call(
                "agent_cmd_agent123",
                {
                    "type": "stream_output",
                    "cmd_id": "err123",
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
