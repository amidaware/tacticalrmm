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
from unittest.mock import AsyncMock

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
        self.consumer.scope = {"user": self.user, "client": ("127.0.0.1", 12345)}
        self.consumer.user = self.user
        self.consumer.channel_name = "test_channel"
        self.consumer.channel_layer = None
        self.consumer.agent_id = self.agent.agent_id
        self.consumer.group_name = f"agent_cmd_{self.agent.agent_id}"

    @patch.object(CommandStreamConsumer, "send_json", autospec=True)
    def test_creates_agent_history_and_auditlog(self, mock_send_json):
        message = {
            "cmd": "ping google.com",
            "shell": "cmd",
            "timeout": 5,
        }

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
