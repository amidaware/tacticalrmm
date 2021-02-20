from unittest.mock import patch

from model_bakery import baker, seq

from core.models import CoreSettings
from core.tasks import core_maintenance_tasks
from tacticalrmm.test import TacticalTestCase


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

    @patch("automation.tasks.generate_all_agent_checks_task.delay")
    def test_edit_coresettings(self, generate_all_agent_checks_task):
        url = "/core/editsettings/"

        # setup
        policies = baker.make("Policy", _quantity=2)
        # test normal request
        data = {
            "smtp_from_email": "newexample@example.com",
            "mesh_token": "New_Mesh_Token",
        }
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            CoreSettings.objects.first().smtp_from_email, data["smtp_from_email"]
        )
        self.assertEqual(CoreSettings.objects.first().mesh_token, data["mesh_token"])

        generate_all_agent_checks_task.assert_not_called()

        # test adding policy
        data = {
            "workstation_policy": policies[0].id,
            "server_policy": policies[1].id,
        }
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CoreSettings.objects.first().server_policy.id, policies[1].id)
        self.assertEqual(
            CoreSettings.objects.first().workstation_policy.id, policies[0].id
        )

        self.assertEqual(generate_all_agent_checks_task.call_count, 2)

        generate_all_agent_checks_task.reset_mock()

        # test remove policy
        data = {
            "workstation_policy": "",
        }
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CoreSettings.objects.first().workstation_policy, None)

        self.assertEqual(generate_all_agent_checks_task.call_count, 1)

        self.check_not_authenticated("patch", url)

    @patch("tacticalrmm.utils.reload_nats")
    @patch("autotasks.tasks.remove_orphaned_win_tasks.delay")
    def test_ui_maintenance_actions(self, remove_orphaned_win_tasks, reload_nats):
        url = "/core/servermaintenance/"

        agents = baker.make_recipe("agents.online_agent", _quantity=3)

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
        reload_nats.assert_called_once()

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

        # test remove orphaned tasks
        data = {"action": "rm_orphaned_tasks"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)
        remove_orphaned_win_tasks.assert_called()

        self.check_not_authenticated("post", url)
