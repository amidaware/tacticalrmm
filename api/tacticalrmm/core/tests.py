from unittest.mock import patch

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .consumers import DashInfo
from .models import CoreSettings, CustomField
from .serializers import CustomFieldSerializer
from .tasks import core_maintenance_tasks


class TestConsumers(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()

    @database_sync_to_async
    def get_token(self):
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.john)
        return token.key

    async def test_dash_info(self):
        key = self.get_token()
        communicator = WebsocketCommunicator(
            DashInfo.as_asgi(), f"/ws/dashinfo/?access_token={key}"
        )
        communicator.scope["user"] = self.john
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()


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
        policies = baker.make("automation.Policy", _quantity=2)
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
            "workstation_policy": policies[0].id,  # type: ignore
            "server_policy": policies[1].id,  # type: ignore
        }
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CoreSettings.objects.first().server_policy.id, policies[1].id)  # type: ignore
        self.assertEqual(
            CoreSettings.objects.first().workstation_policy.id, policies[0].id  # type: ignore
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
            "prune_tables": ["audit_logs", "alerts", "pending_actions"],
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)

        # test remove orphaned tasks
        data = {"action": "rm_orphaned_tasks"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)
        remove_orphaned_win_tasks.assert_called()

        self.check_not_authenticated("post", url)

    def test_get_custom_fields(self):
        url = "/core/customfields/"

        # setup
        custom_fields = baker.make("core.CustomField", _quantity=2)

        r = self.client.get(url)
        serializer = CustomFieldSerializer(custom_fields, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)  # type: ignore
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_custom_fields_by_model(self):
        url = "/core/customfields/"

        # setup
        custom_fields = baker.make("core.CustomField", model="agent", _quantity=5)
        baker.make("core.CustomField", model="client", _quantity=5)

        # will error if request invalid
        r = self.client.patch(url, {"invalid": ""})
        self.assertEqual(r.status_code, 400)

        data = {"model": "agent"}
        r = self.client.patch(url, data)
        serializer = CustomFieldSerializer(custom_fields, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 5)  # type: ignore
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("patch", url)

    def test_add_custom_field(self):
        url = "/core/customfields/"

        data = {"model": "client", "type": "text", "name": "Field"}
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_get_custom_field(self):
        # setup
        custom_field = baker.make("core.CustomField")

        # test not found
        r = self.client.get("/core/customfields/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/customfields/{custom_field.id}/"  # type: ignore
        r = self.client.get(url)
        serializer = CustomFieldSerializer(custom_field)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_update_custom_field(self):
        # setup
        custom_field = baker.make("core.CustomField")

        # test not found
        r = self.client.put("/core/customfields/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/customfields/{custom_field.id}/"  # type: ignore
        data = {"type": "single", "options": ["ione", "two", "three"]}
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)

        new_field = CustomField.objects.get(pk=custom_field.id)  # type: ignore
        self.assertEqual(new_field.type, data["type"])
        self.assertEqual(new_field.options, data["options"])

        self.check_not_authenticated("put", url)

    def test_delete_custom_field(self):
        # setup
        custom_field = baker.make("core.CustomField")

        # test not found
        r = self.client.delete("/core/customfields/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/customfields/{custom_field.id}/"  # type: ignore
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(CustomField.objects.filter(pk=custom_field.id).exists())  # type: ignore

        self.check_not_authenticated("delete", url)
