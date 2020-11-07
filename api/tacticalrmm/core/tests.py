from tacticalrmm.test import TacticalTestCase
from core.tasks import core_maintenance_tasks


class TestCoreTasks(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()

    def test_core_maintenance_tasks(self):
        task = core_maintenance_tasks.s().apply()
        self.assertEqual(task.state, "SUCCESS")

    def test_dashboard_info(self):
        url = "/core/dashinfo/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_vue_version(self):
        url = "/core/version/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_get_core_settings(self):
        url = "/core/getcoresettings/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)
