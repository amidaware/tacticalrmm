from unittest.mock import patch
from model_bakery import baker, seq
from itertools import cycle

from tacticalrmm.test import TacticalTestCase


class TestAutotaskViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    @patch("autotasks.tasks.create_win_task_schedule.delay")
    def test_add_autotask(
        self, create_win_task_schedule, generate_agent_tasks_from_policies_task
    ):
        url = "/autotasks/automatedtasks/"

        script = baker.make_recipe("scripts.script")
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        # test script set to invalid pk
        data = {"autotask": {"script": 500}}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test invalid policy
        data = {"autotask": {"script": script.id}, "policy": 500}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test invalid agent
        data = {"autotask": {"script": script.id}, "agent": 500}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test add task to agent
        data = {
            "autotask": {
                "name": "Test Task",
                "run_time_days": [0, 1, 2],
                "run_time_minute": "10:00",
                "timeout": 120,
                "enabled": True,
                "script": script.id,
                "task_type": "scheduled",
            },
            "agent": agent.pk,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_get_autotask(self):
        pass

    def test_update_autotask(self):
        pass

    def test_delete_autotask(self):
        pass

    def test_run_autotask(self):
        pass
