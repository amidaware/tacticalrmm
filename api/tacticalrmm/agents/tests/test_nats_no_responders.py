import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
from asgiref.sync import sync_to_async
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase
from model_bakery import baker
from nats.errors import NoRespondersError
from nats.errors import TimeoutError as NatsTimeout

from tacticalrmm.constants import TaskSyncStatus
from tacticalrmm.nats_utils import a_nats_cmd, nats_request
from tacticalrmm.test import TacticalTestCase


def make_reply(data):
    msg = MagicMock()
    msg.data = msgpack.dumps(data)
    return msg


def make_nc(responses):
    async def request(subject, payload, timeout):
        resp = responses[subject]
        if isinstance(resp, Exception):
            raise resp
        return make_reply(resp)

    nc = MagicMock()
    nc.request = AsyncMock(side_effect=request)
    nc.publish = AsyncMock()
    nc.flush = AsyncMock()
    nc.close = AsyncMock()
    return nc


class TestNatsRequest(SimpleTestCase):
    def test_no_responders_waits_out_timeout(self):
        nc = make_nc({"agent1": NoRespondersError()})
        start = time.monotonic()
        with self.assertRaises(NatsTimeout):
            asyncio.run(
                nats_request(nc=nc, subject="agent1", payload=b"x", timeout=0.3)
            )
        self.assertGreaterEqual(time.monotonic() - start, 0.29)
        nc.request.assert_awaited_once()

    def test_reply_is_returned(self):
        nc = make_nc({"agent1": "pong"})
        msg = asyncio.run(
            nats_request(nc=nc, subject="agent1", payload=b"x", timeout=1)
        )
        self.assertEqual(msgpack.loads(msg.data), "pong")

    def test_timeout_is_raised_unchanged(self):
        nc = make_nc({"agent1": NatsTimeout()})
        with self.assertRaises(NatsTimeout):
            asyncio.run(nats_request(nc=nc, subject="agent1", payload=b"x", timeout=5))

    def test_a_nats_cmd_no_responders(self):
        nc = make_nc({"agent1": NoRespondersError()})
        r = asyncio.run(
            a_nats_cmd(nc=nc, sub="agent1", data={"func": "ping"}, timeout=0.1)
        )
        self.assertEqual(r, "timeout")

    def test_gather_keeps_other_agents_results(self):
        nc = make_nc({"online": "pong", "offline": NoRespondersError()})

        async def run():
            return await asyncio.gather(
                a_nats_cmd(nc=nc, sub="online", data={"func": "ping"}, timeout=0.1),
                a_nats_cmd(nc=nc, sub="offline", data={"func": "ping"}, timeout=0.1),
            )

        self.assertEqual(asyncio.run(run()), ["pong", "timeout"])


class TestAgentsNoResponders(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.nats.connect", new_callable=AsyncMock)
    def test_nats_cmd_no_responders(self, nats_connect):
        agent = baker.make_recipe("agents.online_agent")
        nc = make_nc({agent.agent_id: NoRespondersError()})
        nats_connect.return_value = nc

        r = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=0.2))

        self.assertEqual(r, "timeout")
        nc.close.assert_awaited_once()

    @patch("agents.views.time.sleep")
    @patch("tacticalrmm.nats_utils.asyncio.sleep", new_callable=AsyncMock)
    @patch("agents.models.nats.connect", new_callable=AsyncMock)
    def test_ping_disconnected_agent(self, nats_connect, nats_sleep, view_sleep):
        agent = baker.make_recipe("agents.offline_agent")
        nats_connect.return_value = make_nc({agent.agent_id: NoRespondersError()})

        r = self.client.get(f"/agents/{agent.agent_id}/ping/", format="json")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "offline")
        self.assertEqual(nats_sleep.await_count, 3)

    @patch("tacticalrmm.nats_utils.asyncio.sleep", new_callable=AsyncMock)
    @patch("autotasks.tasks.nats.connect", new_callable=AsyncMock)
    def test_remove_orphaned_win_tasks_disconnected_agent(
        self, nats_connect, nats_sleep
    ):
        from autotasks.tasks import remove_orphaned_win_tasks

        disconnected = baker.make_recipe("agents.online_agent")
        connected = baker.make_recipe("agents.online_agent")
        nc = make_nc(
            {
                disconnected.agent_id: NoRespondersError(),
                connected.agent_id: ["TacticalRMM_orphan"],
            }
        )
        nats_connect.return_value = nc

        self.assertEqual(remove_orphaned_win_tasks(), "completed")

        nc.publish.assert_awaited_once()
        self.assertEqual(nc.publish.await_args.kwargs["subject"], connected.agent_id)

    @patch("tacticalrmm.nats_utils.asyncio.sleep", new_callable=AsyncMock)
    @patch("agents.models.nats.connect", new_callable=AsyncMock)
    def test_agent_outages_with_script_action(self, nats_connect, nats_sleep):
        from agents.tasks import agent_outages_task
        from alerts.models import Alert
        from alerts.tasks import cache_agents_alert_template

        script = baker.make("scripts.Script")
        template = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            agent_always_alert=True,
            agent_script_actions=True,
            action_type="script",
            action=script,
        )
        overdue = [baker.make_recipe("agents.overdue_agent") for _ in range(2)]
        for agent in overdue:
            agent.client.alert_template = template
            agent.client.save()
        cache_agents_alert_template()
        nats_connect.return_value = make_nc(
            {agent.agent_id: NoRespondersError() for agent in overdue}
        )

        agent_outages_task()

        for agent in overdue:
            self.assertEqual(
                Alert.objects.filter(agent=agent, resolved=False).count(), 1
            )


class TestSyncScheduledTasksNoResponders(TransactionTestCase):
    # sync_scheduled_tasks reads tasks with the async ORM on its own connection,
    # so the test data has to be committed

    def tearDown(self):
        # close the async ORM's connection so the test db can be dropped
        asyncio.run(sync_to_async(connections.close_all)())

    @patch("tacticalrmm.nats_utils.asyncio.sleep", new_callable=AsyncMock)
    @patch("core.tasks.nats.connect", new_callable=AsyncMock)
    def test_sync_scheduled_tasks_disconnected_agent(self, nats_connect, nats_sleep):
        from core.tasks import sync_scheduled_tasks

        disconnected = baker.make_recipe("agents.online_agent", version="2.12.0")
        connected = baker.make_recipe("agents.online_agent", version="2.12.0")
        results = {}
        for agent in (disconnected, connected):
            task = baker.make(
                "autotasks.AutomatedTask", agent=agent, task_type="manual"
            )
            results[agent.pk] = baker.make(
                "autotasks.TaskResult",
                agent=agent,
                task=task,
                sync_status=TaskSyncStatus.NOT_SYNCED,
            )
        nats_connect.return_value = make_nc(
            {disconnected.agent_id: NoRespondersError(), connected.agent_id: "ok"}
        )

        self.assertEqual(sync_scheduled_tasks(), "ok")

        results[disconnected.pk].refresh_from_db()
        results[connected.pk].refresh_from_db()
        self.assertEqual(
            results[disconnected.pk].sync_status, TaskSyncStatus.NOT_SYNCED
        )
        self.assertEqual(results[connected.pk].sync_status, TaskSyncStatus.SYNCED)
