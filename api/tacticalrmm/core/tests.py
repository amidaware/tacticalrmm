from unittest.mock import patch

import requests
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from model_bakery import baker
from rest_framework.authtoken.models import Token

from tacticalrmm.test import TacticalTestCase
from core.utils import get_core_settings
from .consumers import DashInfo
from .models import CustomField, GlobalKVStore, URLAction
from .serializers import CustomFieldSerializer, KeyStoreSerializer, URLActionSerializer
from .tasks import core_maintenance_tasks


class TestCodeSign(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()
        self.url = "/core/codesign/"

    def test_get_codesign(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", self.url)

    @patch("requests.post")
    def test_edit_codesign_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()
        data = {"token": "token123"}
        r = self.client.patch(self.url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("patch", self.url)


class TestConsumers(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()

    @database_sync_to_async
    def get_token(self):

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
        core_maintenance_tasks()
        self.assertTrue(True)

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
        url = "/core/settings/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_edit_coresettings(self):
        url = "/core/settings/"

        # setup
        policies = baker.make("automation.Policy", _quantity=2)
        # test normal request
        data = {
            "smtp_from_email": "newexample@example.com",
            "mesh_token": "New_Mesh_Token",
        }
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(get_core_settings().smtp_from_email, data["smtp_from_email"])
        self.assertEqual(get_core_settings().mesh_token, data["mesh_token"])

        self.check_not_authenticated("put", url)

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
        self.assertEqual(len(r.data), 2)
        self.assertEqual(r.data, serializer.data)

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
        self.assertEqual(len(r.data), 5)

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

        url = f"/core/customfields/{custom_field.id}/"
        r = self.client.get(url)
        serializer = CustomFieldSerializer(custom_field)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_update_custom_field(self):
        # setup
        custom_field = baker.make("core.CustomField")

        # test not found
        r = self.client.put("/core/customfields/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/customfields/{custom_field.id}/"
        data = {"type": "single", "options": ["ione", "two", "three"]}
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)

        new_field = CustomField.objects.get(pk=custom_field.id)
        self.assertEqual(new_field.type, data["type"])
        self.assertEqual(new_field.options, data["options"])

        self.check_not_authenticated("put", url)

    def test_delete_custom_field(self):
        # setup
        custom_field = baker.make("core.CustomField")

        # test not found
        r = self.client.delete("/core/customfields/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/customfields/{custom_field.id}/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(CustomField.objects.filter(pk=custom_field.id).exists())

        self.check_not_authenticated("delete", url)

    def test_get_keystore(self):
        url = "/core/keystore/"

        # setup
        keys = baker.make("core.GlobalKVStore", _quantity=2)

        r = self.client.get(url)
        serializer = KeyStoreSerializer(keys, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_keystore(self):
        url = "/core/keystore/"

        data = {"name": "test", "value": "text"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_update_keystore(self):
        # setup
        key = baker.make("core.GlobalKVStore")

        # test not found
        r = self.client.put("/core/keystore/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/keystore/{key.id}/"
        data = {"name": "test", "value": "text"}
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)

        new_key = GlobalKVStore.objects.get(pk=key.id)
        self.assertEqual(new_key.name, data["name"])
        self.assertEqual(new_key.value, data["value"])

        self.check_not_authenticated("put", url)

    def test_delete_keystore(self):
        # setup
        key = baker.make("core.GlobalKVStore")

        # test not found
        r = self.client.delete("/core/keystore/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/keystore/{key.id}/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(GlobalKVStore.objects.filter(pk=key.id).exists())

        self.check_not_authenticated("delete", url)

    def test_get_urlaction(self):
        url = "/core/urlaction/"

        # setup
        action = baker.make("core.URLAction", _quantity=2)

        r = self.client.get(url)
        serializer = URLActionSerializer(action, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_urlaction(self):
        url = "/core/urlaction/"

        data = {"name": "name", "desc": "desc", "pattern": "pattern"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_update_urlaction(self):
        # setup
        action = baker.make("core.URLAction")

        # test not found
        r = self.client.put("/core/urlaction/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/urlaction/{action.id}/"
        data = {"name": "test", "pattern": "text"}
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)

        new_action = URLAction.objects.get(pk=action.id)
        self.assertEqual(new_action.name, data["name"])
        self.assertEqual(new_action.pattern, data["pattern"])

        self.check_not_authenticated("put", url)

    def test_delete_urlaction(self):
        # setup
        action = baker.make("core.URLAction")

        # test not found
        r = self.client.delete("/core/urlaction/500/")
        self.assertEqual(r.status_code, 404)

        url = f"/core/urlaction/{action.id}/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(URLAction.objects.filter(pk=action.id).exists())

        self.check_not_authenticated("delete", url)

    def test_run_url_action(self):
        self.maxDiff = None
        # setup
        agent = baker.make_recipe(
            "agents.agent", agent_id="123123-assdss4s-343-sds545-45dfdf|DESKTOP"
        )
        baker.make("core.GlobalKVStore", name="Test Name", value="value with space")
        action = baker.make(
            "core.URLAction",
            pattern="https://remote.example.com/connect?globalstore={{global.Test Name}}&client_name={{client.name}}&site id={{site.id}}&agent_id={{agent.agent_id}}",
        )

        url = "/core/urlaction/run/"
        # test not found
        r = self.client.patch(url, {"agent_id": 500, "action": 500})
        self.assertEqual(r.status_code, 404)

        data = {"agent_id": agent.agent_id, "action": action.id}
        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(
            r.data,
            f"https://remote.example.com/connect?globalstore=value%20with%20space&client_name={agent.client.name}&site%20id={agent.site.id}&agent_id=123123-assdss4s-343-sds545-45dfdf%7CDESKTOP",
        )

        self.check_not_authenticated("patch", url)


class TestCorePermissions(TacticalTestCase):
    def setUp(self):
        self.setup_client()
        self.setup_coresettings()
