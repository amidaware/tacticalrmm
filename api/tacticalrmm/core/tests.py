import os
from unittest.mock import patch

import requests
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

# from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from model_bakery import baker
from rest_framework.authtoken.models import Token

# from agents.models import Agent
from core.utils import get_core_settings, get_mesh_ws_url, get_meshagent_url

# from logs.models import PendingAction
from tacticalrmm.constants import (  # PAAction,; PAStatus,
    CONFIG_MGMT_CMDS,
    CustomFieldModel,
    MeshAgentIdent,
)
from tacticalrmm.helpers import get_nats_hosts, get_nats_url
from tacticalrmm.test import TacticalTestCase

from .consumers import DashInfo
from .models import CustomField, GlobalKVStore, URLAction
from .serializers import CustomFieldSerializer, KeyStoreSerializer, URLActionSerializer
from .tasks import core_maintenance_tasks  # , resolve_pending_actions


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

    def test_delete_codesign(self):
        r = self.client.delete(self.url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("delete", self.url)


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
        baker.make("automation.Policy", _quantity=2)
        # test normal request
        data = {
            "smtp_from_email": "newexample@example.com",
            "mesh_token": "New_Mesh_Token",
            "mesh_site": "https://mesh.example.com",
            "mesh_username": "bob",
            "sync_mesh_with_trmm": False,
        }
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)
        core = get_core_settings()
        self.assertEqual(core.smtp_from_email, "newexample@example.com")
        self.assertEqual(core.mesh_token, "New_Mesh_Token")
        self.assertEqual(core.mesh_site, "https://mesh.example.com")
        self.assertEqual(core.mesh_username, "bob")
        self.assertFalse(core.sync_mesh_with_trmm)

        # test to_representation
        r = self.client.get(url)
        self.assertEqual(r.data["smtp_from_email"], "newexample@example.com")
        self.assertEqual(r.data["mesh_token"], "New_Mesh_Token")
        self.assertEqual(r.data["mesh_site"], "https://mesh.example.com")
        self.assertEqual(r.data["mesh_username"], "bob")
        self.assertFalse(r.data["sync_mesh_with_trmm"])

        self.check_not_authenticated("put", url)

    @override_settings(HOSTED=True)
    def test_hosted_edit_coresettings(self):
        url = "/core/settings/"
        baker.make("automation.Policy", _quantity=2)
        data = {
            "smtp_from_email": "newexample1@example.com",
            "mesh_token": "abc123",
            "mesh_site": "https://mesh15534.example.com",
            "mesh_username": "jane",
            "sync_mesh_with_trmm": False,
        }
        r = self.client.put(url, data)
        self.assertEqual(r.status_code, 200)
        core = get_core_settings()
        self.assertEqual(core.smtp_from_email, "newexample1@example.com")
        self.assertIn("41410834b8bb4481446027f8", core.mesh_token)  # type: ignore
        self.assertTrue(core.sync_mesh_with_trmm)
        if "GHACTIONS" in os.environ:
            self.assertEqual(core.mesh_site, "https://example.com")
            self.assertEqual(core.mesh_username, "pipeline")

        # test to_representation
        r = self.client.get(url)
        self.assertEqual(r.data["smtp_from_email"], "newexample1@example.com")
        self.assertEqual(r.data["mesh_token"], "n/a")
        self.assertEqual(r.data["mesh_site"], "n/a")
        self.assertEqual(r.data["mesh_username"], "n/a")
        self.assertTrue(r.data["sync_mesh_with_trmm"])

        self.check_not_authenticated("put", url)

    @patch("tacticalrmm.utils.reload_nats")
    @patch("autotasks.tasks.remove_orphaned_win_tasks.delay")
    def test_ui_maintenance_actions(self, remove_orphaned_win_tasks, reload_nats):
        url = "/core/servermaintenance/"

        baker.make_recipe("agents.online_agent", _quantity=3)

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
        baker.make("core.CustomField", model=CustomFieldModel.AGENT, _quantity=5)
        baker.make("core.CustomField", model="client", _quantity=5)

        # will error if request invalid
        r = self.client.patch(url, {"invalid": ""})
        self.assertEqual(r.status_code, 400)

        data = {"model": "agent"}
        r = self.client.patch(url, data)
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

    def test_clear_cache(self):
        url = "/core/clearcache/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    # def test_resolved_pending_agentupdate_task(self):
    #     online = baker.make_recipe("agents.online_agent", version="2.0.0", _quantity=20)
    #     offline = baker.make_recipe(
    #         "agents.offline_agent", version="2.0.0", _quantity=20
    #     )
    #     agents = online + offline
    #     for agent in agents:
    #         baker.make_recipe("logs.pending_agentupdate_action", agent=agent)

    #     Agent.objects.update(version=settings.LATEST_AGENT_VER)

    #     resolve_pending_actions()

    #     complete = PendingAction.objects.filter(
    #         action_type=PAAction.AGENT_UPDATE, status=PAStatus.COMPLETED
    #     ).count()
    #     old = PendingAction.objects.filter(
    #         action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
    #     ).count()

    #     self.assertEqual(complete, 20)
    #     self.assertEqual(old, 20)


class TestCoreMgmtCommands(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_get_config(self):
        for cmd in CONFIG_MGMT_CMDS:
            call_command("get_config", cmd)


class TestNatsUrls(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_standard_install(self):
        self.assertEqual(get_nats_url(), "nats://127.0.0.1:4222")

    @override_settings(
        NATS_STANDARD_PORT=5000,
        USE_NATS_STANDARD=True,
        ALLOWED_HOSTS=["api.example.com"],
    )
    def test_custom_port_nats_standard(self):
        self.assertEqual(get_nats_url(), "tls://api.example.com:5000")

    @override_settings(DOCKER_BUILD=True, ALLOWED_HOSTS=["api.example.com"])
    def test_docker_nats(self):
        self.assertEqual(get_nats_url(), "nats://api.example.com:4222")

    @patch.dict("os.environ", {"NATS_CONNECT_HOST": "172.20.4.3"})
    @override_settings(ALLOWED_HOSTS=["api.example.com"])
    def test_custom_connect_host_env(self):
        self.assertEqual(get_nats_url(), "nats://172.20.4.3:4222")

    def test_standard_nats_hosts(self):
        self.assertEqual(get_nats_hosts(), ("127.0.0.1", "127.0.0.1", "127.0.0.1"))

    @override_settings(DOCKER_BUILD=True, ALLOWED_HOSTS=["api.example.com"])
    def test_docker_nats_hosts(self):
        self.assertEqual(get_nats_hosts(), ("0.0.0.0", "0.0.0.0", "api.example.com"))


class TestMeshWSUrl(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    @patch("core.utils.get_auth_token")
    def test_standard_install(self, mock_token):
        mock_token.return_value = "abc123"
        self.assertEqual(
            get_mesh_ws_url(), "ws://127.0.0.1:4430/control.ashx?auth=abc123"
        )

    @patch("core.utils.get_auth_token")
    @override_settings(MESH_PORT=8876)
    def test_standard_install_custom_port(self, mock_token):
        mock_token.return_value = "abc123"
        self.assertEqual(
            get_mesh_ws_url(), "ws://127.0.0.1:8876/control.ashx?auth=abc123"
        )

    @patch("core.utils.get_auth_token")
    @override_settings(DOCKER_BUILD=True, MESH_WS_URL="ws://tactical-meshcentral:4443")
    def test_docker_install(self, mock_token):
        mock_token.return_value = "abc123"
        self.assertEqual(
            get_mesh_ws_url(), "ws://tactical-meshcentral:4443/control.ashx?auth=abc123"
        )

    @patch("core.utils.get_auth_token")
    @override_settings(USE_EXTERNAL_MESH=True)
    def test_external_mesh(self, mock_token):
        mock_token.return_value = "abc123"

        from core.models import CoreSettings

        core = CoreSettings.objects.first()
        core.mesh_site = "https://mesh.external.com"  # type: ignore
        core.save(update_fields=["mesh_site"])  # type: ignore
        self.assertEqual(
            get_mesh_ws_url(), "wss://mesh.external.com/control.ashx?auth=abc123"
        )


class TestCorePermissions(TacticalTestCase):
    def setUp(self):
        self.setup_client()
        self.setup_coresettings()


class TestCoreUtils(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_get_meshagent_url_standard(self):
        r = get_meshagent_url(
            ident=MeshAgentIdent.DARWIN_UNIVERSAL,
            plat="darwin",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://127.0.0.1:4430/meshagents?id=abc123&installflags=2&meshinstall=10005",
        )

        r = get_meshagent_url(
            ident=MeshAgentIdent.WIN64,
            plat="windows",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://127.0.0.1:4430/meshagents?id=4&meshid=abc123&installflags=0",
        )

    @override_settings(DOCKER_BUILD=True)
    @override_settings(MESH_WS_URL="ws://tactical-meshcentral:4443")
    def test_get_meshagent_url_docker(self):
        r = get_meshagent_url(
            ident=MeshAgentIdent.DARWIN_UNIVERSAL,
            plat="darwin",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://tactical-meshcentral:4443/meshagents?id=abc123&installflags=2&meshinstall=10005",
        )

        r = get_meshagent_url(
            ident=MeshAgentIdent.WIN64,
            plat="windows",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://tactical-meshcentral:4443/meshagents?id=4&meshid=abc123&installflags=0",
        )

    @override_settings(USE_EXTERNAL_MESH=True)
    def test_get_meshagent_url_external_mesh(self):
        r = get_meshagent_url(
            ident=MeshAgentIdent.DARWIN_UNIVERSAL,
            plat="darwin",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "https://mesh.example.com/meshagents?id=abc123&installflags=2&meshinstall=10005",
        )

        r = get_meshagent_url(
            ident=MeshAgentIdent.WIN64,
            plat="windows",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "https://mesh.example.com/meshagents?id=4&meshid=abc123&installflags=0",
        )

    @override_settings(MESH_PORT=8653)
    def test_get_meshagent_url_mesh_port(self):
        r = get_meshagent_url(
            ident=MeshAgentIdent.DARWIN_UNIVERSAL,
            plat="darwin",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://127.0.0.1:8653/meshagents?id=abc123&installflags=2&meshinstall=10005",
        )

        r = get_meshagent_url(
            ident=MeshAgentIdent.WIN64,
            plat="windows",
            mesh_site="https://mesh.example.com",
            mesh_device_id="abc123",
        )
        self.assertEqual(
            r,
            "http://127.0.0.1:8653/meshagents?id=4&meshid=abc123&installflags=0",
        )
