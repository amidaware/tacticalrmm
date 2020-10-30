from unittest.mock import patch
from model_bakery import baker, seq
from itertools import cycle

from tacticalrmm.test import TacticalTestCase


class TestAutotaskViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    def test_add_autotask(self, generate_agent_tasks_from_policies_task):
        pass

    def test_get_autotask(self):
        pass

    def test_update_autotask(self):
        pass

    def test_delete_autotask(self):
        pass
