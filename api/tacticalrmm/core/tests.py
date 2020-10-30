from tacticalrmm.test import BaseTestCase
from core.tasks import core_maintenance_tasks


class TestCoreTasks(BaseTestCase):
    def test_core_maintenance_tasks(self):
        task = core_maintenance_tasks.s().apply()
        self.assertEqual(task.state, "SUCCESS")
