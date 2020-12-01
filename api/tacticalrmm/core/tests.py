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

    def test_ui_maintenance_actions(self):
        url = "/core/servermaintenance/"

        # test with empty data
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 400)

        # test with invalid action
        data = {"action": "invalid_action"}

        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 400)

        # test reload nats action
        data = {"action": "reload_nats"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)

        # test prune db with no tables
        data = {"action": "prune_db"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 400)

        # test prune db with tables
        data = {
            "action": "prune_db",
            "prune_tables": ["audit_logs", "agent_outages", "pending_actions"],
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)
