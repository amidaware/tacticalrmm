from unittest.mock import patch

import tempfile
import requests
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from model_bakery import baker
from rest_framework.authtoken.models import Token

from agents.models import Agent
from core.utils import get_core_settings, get_meshagent_url
from logs.models import PendingAction
from tacticalrmm.constants import (
    CONFIG_MGMT_CMDS,
    CustomFieldModel,
    MeshAgentIdent,
    PAAction,
    PAStatus,
)
from tacticalrmm.test import TacticalTestCase

from .consumers import DashInfo
from .models import CustomField, GlobalKVStore, URLAction
from .serializers import CustomFieldSerializer, KeyStoreSerializer, URLActionSerializer
from .tasks import core_maintenance_tasks, resolve_pending_actions


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

    def test_resolved_pending_agentupdate_task(self):
        online = baker.make_recipe("agents.online_agent", version="2.0.0", _quantity=20)
        offline = baker.make_recipe(
            "agents.offline_agent", version="2.0.0", _quantity=20
        )
        agents = online + offline
        for agent in agents:
            baker.make_recipe("logs.pending_agentupdate_action", agent=agent)

        Agent.objects.update(version=settings.LATEST_AGENT_VER)

        resolve_pending_actions()

        complete = PendingAction.objects.filter(
            action_type=PAAction.AGENT_UPDATE, status=PAStatus.COMPLETED
        ).count()
        old = PendingAction.objects.filter(
            action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
        ).count()

        self.assertEqual(complete, 20)
        self.assertEqual(old, 20)


class TestCoreMgmtCommands(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_get_config(self):
        for cmd in CONFIG_MGMT_CMDS:
            call_command("get_config", cmd)


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


class TestMonitoring(TacticalTestCase):
    url = "/core/status/"

    def setUp(self):
        self.setup_client()
        self.setup_coresettings()

        # sample data for generated metrics
        client1 = baker.make("clients.Client")
        client1_site1 = baker.make("clients.Site", client=client1)
        client1_site2 = baker.make("clients.Site", client=client1)
        baker.make("agents.agent", _quantity=10, site=client1_site1)
        baker.make("agents.agent", _quantity=13, site=client1_site2)
        client2 = baker.make("clients.Client")
        client2_site1 = baker.make("clients.Site", client=client2)
        baker.make("agents.agent", _quantity=13, site=client2_site1)

        # Generate snakeoil cert with `make-ssl-cert generate-default-snakeoil` on ubuntu
        # Cert will be in '/etc/ssl/certs/ssl-cert-snakeoil.pem'.
        # Cert is used only for expiration date, so it can be selfsigned, expired and no key is needed.
        self.snakeoil_certificate = tempfile.NamedTemporaryFile(delete=False)
        self.snakeoil_certificate.write(
            """-----BEGIN CERTIFICATE-----
MIIC4jCCAcqgAwIBAgIUCFgTym78sGgRHwEmLyGgmr1JjSUwDQYJKoZIhvcNAQEL
BQAwFzEVMBMGA1UEAwwMZjNjMTQzOWM0NzZjMB4XDTIzMDMzMTA1MTgzOFoXDTMz
MDMyODA1MTgzOFowFzEVMBMGA1UEAwwMZjNjMTQzOWM0NzZjMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzFWItB4aM/aUWIhk0SS1XKHLHao9/OwbGHet
lnrlZD2YM/DdUzqdYeYdujyLvWUj1xU+YcFv+vo3Mmu8HQVOKNcEZ5ZilHW/87X8
6ZjtUzPYmCapxXNTX8yh2EES582uq64j0t3OwfaCJmpJLwjvCnrizfUFe76iy5Ge
wVviYtkaIfHEwNoJLmFb07rYhNuV4tiwHUhmZqqm5nxpjKbTsI4YHnpSxNktU32C
vNVnIRIAHDZ8n8wCaKTPZMui9X/IJx1pA3EkbD2givbH/0nYRcd5ZUDxLsTJThob
8k5kPd1zVXqaH/ufqkekqoiY+kIWsgVd0iWx3qihhydAhRY5SQIDAQABoyYwJDAJ
BgNVHRMEAjAAMBcGA1UdEQQQMA6CDGYzYzE0MzljNDc2YzANBgkqhkiG9w0BAQsF
AAOCAQEAH91bAuK3tKf1v4D+t48SWSE2uFjCe6o2CzMwAdM3rVa47X2cw5nKOH5L
8nQJhJjq/t93DJi4WOpN579NWtTkwXyCl7srSvj8aK4FDKxKcWQNT1PUAa+gh8IB
WJdEK4lMSatCtA/wsq6jmkTwINZ/ELZp4BRU2gUp8mFU9fVQDMlY+2qwUzzIp97A
WISWVxML58FDFnQLsaP1SfapVWTTXTh4xnhr7VxklUadcGRnx9+Ig4Ieq27eSCiV
DC/aSRIyi9HaVZPTMbqLC50auHr/dQIL4pGyxFTD8OJoeRkQgAb1wWuAPhab20Xu
XyFzZMiRlyNNSPoYVExb65s1bawqew==
-----END CERTIFICATE-----""".encode(
                encoding="utf-8"
            )
        )
        self.snakeoil_certificate.close()

    def tearDown(self):
        from os import unlink

        unlink(self.snakeoil_certificate.name)

    # prometheus tests
    def test_prometheus_missing_auth_header_request(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    def test_prometheus_missing_token_config(self):
        r = self.client.get(self.url, HTTP_Authorization="Bearer MySuperTestSecret")
        self.assertEqual(r.status_code, 401)

    @override_settings(MON_TOKEN="MySuperTestSecret")
    def test_prometheus_incorrect_token_request(self):
        r = self.client.get(self.url, HTTP_Authorization="Bearer NotMySuperTestSecret")
        self.assertEqual(r.status_code, 401)

    @override_settings(DOCKER_BUILD=True, MON_TOKEN="MySuperTestSecret")
    def test_prometheus_correct_docker_build_request(self):
        with self.settings(
            CERT_FILE=self.snakeoil_certificate.name, KEY_FILE="/do/not/need/a/key/here"
        ):
            r = self.client.get(self.url, HTTP_Authorization="Bearer MySuperTestSecret")
            self.assertEqual(r.status_code, 200)

    @override_settings(MON_TOKEN="MySuperTestSecret")
    def test_prometheus_correct_request(self):
        with self.settings(
            CERT_FILE=self.snakeoil_certificate.name, KEY_FILE="/do/not/need/a/key/here"
        ):
            r = self.client.get(self.url, HTTP_Authorization="Bearer MySuperTestSecret")
            self.assertEqual(r.status_code, 200)

    # invalid tests
    def test_invalid_request(self):
        r = self.client.put(self.url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.content,
            b"Invalid request type\n",
        )

    # json tests
    def test_json_invalid_json_request(self):
        r = self.client.post(
            self.url,
            data="I am not json!",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_json_invalid_payload_request(self):
        r = self.client.post(
            self.url, data={"notauth": "NotMySuperTestSecret"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_json_missing_token_request(self):
        r = self.client.post(
            self.url, data={"auth": "MySuperTestSecret"}, format="json"
        )
        self.assertEqual(r.status_code, 401)

    @override_settings(MON_TOKEN="MySuperTestSecret")
    def test_json_incorrect_token_request(self):
        r = self.client.post(
            self.url, data={"auth": "NotMySuperTestSecret"}, format="json"
        )
        self.assertEqual(r.status_code, 401)

    @override_settings(MON_TOKEN="MySuperTestSecret")
    def test_json_correct_request(self):
        with self.settings(
            CERT_FILE=self.snakeoil_certificate.name, KEY_FILE="/do/not/need/a/key/here"
        ):
            r = self.client.post(
                self.url, data={"auth": "MySuperTestSecret"}, format="json"
            )
            self.assertEqual(r.status_code, 200)

    @override_settings(DOCKER_BUILD=True, MON_TOKEN="MySuperTestSecret")
    def test_json_correct_docker_build_request(self):
        with self.settings(
            CERT_FILE=self.snakeoil_certificate.name, KEY_FILE="/do/not/need/a/key/here"
        ):
            r = self.client.post(
                self.url, data={"auth": "MySuperTestSecret"}, format="json"
            )
            self.assertEqual(r.status_code, 200)
