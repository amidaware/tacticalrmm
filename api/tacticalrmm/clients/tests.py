import uuid
from unittest.mock import patch

from model_bakery import baker
from rest_framework.serializers import ValidationError

from tacticalrmm.test import TacticalTestCase

from .models import Client, ClientCustomField, Deployment, Site, SiteCustomField
from .serializers import (
    ClientSerializer,
    ClientTreeSerializer,
    DeploymentSerializer,
    SiteSerializer,
)


class TestClientViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_clients(self):
        # setup data
        baker.make("clients.Client", _quantity=5)
        clients = Client.objects.all()

        url = "/clients/clients/"
        r = self.client.get(url, format="json")
        serializer = ClientSerializer(clients, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_add_client(self):
        url = "/clients/clients/"

        # test successfull add client
        payload = {
            "client": {"name": "Client1"},
            "site": {"name": "Site1"},
            "custom_fields": [],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        # test add client with | in name
        payload = {
            "client": {"name": "Client2|d"},
            "site": {"name": "Site1"},
            "custom_fields": [],
        }
        serializer = ClientSerializer(data=payload["client"])
        with self.assertRaisesMessage(
            ValidationError, "Client name cannot contain the | character"
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test add client with | in Site name
        payload = {
            "client": {"name": "Client2"},
            "site": {"name": "Site1|fds"},
            "custom_fields": [],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test unique
        payload = {
            "client": {"name": "Client1"},
            "site": {"name": "Site1"},
            "custom_fields": [],
        }
        serializer = ClientSerializer(data=payload["client"])
        with self.assertRaisesMessage(
            ValidationError, "client with this name already exists."
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test initial setup
        payload = {
            "client": {"name": "Setup Client"},
            "site": {"name": "Setup  Site"},
            "timezone": "America/Los_Angeles",
            "initialsetup": True,
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        # test add with custom fields
        field = baker.make("core.CustomField", model="client", type="text")
        payload = {
            "client": {"name": "Custom Field Client"},
            "site": {"name": "Setup  Site"},
            "custom_fields": [{"field": field.id, "string_value": "new Value"}],  # type: ignore
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        client = Client.objects.get(name="Custom Field Client")
        self.assertTrue(
            ClientCustomField.objects.filter(client=client, field=field).exists()
        )

        self.check_not_authenticated("post", url)

    def test_get_client(self):
        # setup data
        client = baker.make("clients.Client")

        url = f"/clients/{client.id}/client/"  # type: ignore
        r = self.client.get(url, format="json")
        serializer = ClientSerializer(client)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_edit_client(self):
        # setup data
        client = baker.make("clients.Client", name="OldClientName")

        # test invalid id
        r = self.client.put("/clients/500/client/", format="json")
        self.assertEqual(r.status_code, 404)

        # test successfull edit client
        data = {"client": {"name": "NewClientName"}, "custom_fields": []}
        url = f"/clients/{client.id}/client/"  # type: ignore
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Client.objects.filter(name="NewClientName").exists())
        self.assertFalse(Client.objects.filter(name="OldClientName").exists())

        # test edit client with | in name
        data = {"client": {"name": "NewClie|ntName"}, "custom_fields": []}
        url = f"/clients/{client.id}/client/"  # type: ignore
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        # test add with custom fields new value
        field = baker.make("core.CustomField", model="client", type="checkbox")
        payload = {
            "client": {
                "id": client.id,  # type: ignore
                "name": "Custom Field Client",
            },
            "custom_fields": [{"field": field.id, "bool_value": True}],  # type: ignore
        }
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        client = Client.objects.get(name="Custom Field Client")
        self.assertTrue(
            ClientCustomField.objects.filter(client=client, field=field).exists()
        )

        # edit custom field value
        payload = {
            "client": {
                "id": client.id,  # type: ignore
                "name": "Custom Field Client",
            },
            "custom_fields": [{"field": field.id, "bool_value": False}],  # type: ignore
        }
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.assertFalse(
            ClientCustomField.objects.get(client=client, field=field).value
        )

        self.check_not_authenticated("put", url)

    def test_delete_client(self):
        from agents.models import Agent

        # setup data
        client_to_delete = baker.make("clients.Client")
        client_to_move = baker.make("clients.Client")
        site_to_move = baker.make("clients.Site", client=client_to_move)
        agent = baker.make_recipe("agents.agent", site=site_to_move)

        # test invalid id
        r = self.client.delete("/clients/334/953/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/{client_to_delete.id}/{site_to_move.id}/"  # type: ignore

        # test successful deletion
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        agent_moved = Agent.objects.get(pk=agent.pk)
        self.assertEqual(agent_moved.site.id, site_to_move.id)  # type: ignore
        self.assertFalse(Client.objects.filter(pk=client_to_delete.id).exists())  # type: ignore

        self.check_not_authenticated("delete", url)

    def test_get_sites(self):
        # setup data
        baker.make("clients.Site", _quantity=5)
        sites = Site.objects.all()

        url = "/clients/sites/"
        r = self.client.get(url, format="json")
        serializer = SiteSerializer(sites, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_add_site(self):
        # setup data
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)

        url = "/clients/sites/"

        # test success add
        payload = {
            "site": {"client": client.id, "name": "LA Office"},  # type: ignore
            "custom_fields": [],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        # test with | symbol
        payload = {
            "site": {"client": client.id, "name": "LA Office  |*&@#$"},  # type: ignore
            "custom_fields": [],
        }
        serializer = SiteSerializer(data=payload["site"])
        with self.assertRaisesMessage(
            ValidationError, "Site name cannot contain the | character"
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test site already exists
        payload = {
            "site": {"client": site.client.id, "name": "LA Office"},  # type: ignore
            "custom_fields": [],
        }
        serializer = SiteSerializer(data=payload["site"])
        with self.assertRaisesMessage(
            ValidationError, "The fields client, name must make a unique set."
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        # test add with custom fields
        field = baker.make(
            "core.CustomField",
            model="site",
            type="single",
            options=["one", "two", "three"],
        )
        payload = {
            "site": {"client": client.id, "name": "Custom Field Site"},  # type: ignore
            "custom_fields": [{"field": field.id, "string_value": "one"}],  # type: ignore
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        site = Site.objects.get(name="Custom Field Site")
        self.assertTrue(SiteCustomField.objects.filter(site=site, field=field).exists())

        self.check_not_authenticated("post", url)

    def test_get_site(self):
        # setup data
        site = baker.make("clients.Site")

        url = f"/clients/sites/{site.id}/"  # type: ignore
        r = self.client.get(url, format="json")
        serializer = SiteSerializer(site)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_edit_site(self):
        # setup data
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)

        # test invalid id
        r = self.client.put("/clients/sites/688/", format="json")
        self.assertEqual(r.status_code, 404)

        data = {
            "site": {"client": client.id, "name": "New Site Name"},  # type: ignore
            "custom_fields": [],
        }

        url = f"/clients/sites/{site.id}/"  # type: ignore
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            Site.objects.filter(client=client, name="New Site Name").exists()
        )

        # test add with custom fields new value
        field = baker.make(
            "core.CustomField",
            model="site",
            type="multiple",
            options=["one", "two", "three"],
        )
        payload = {
            "site": {
                "id": site.id,  # type: ignore
                "client": site.client.id,  # type: ignore
                "name": "Custom Field Site",
            },
            "custom_fields": [{"field": field.id, "multiple_value": ["two", "three"]}],  # type: ignore
        }
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        site = Site.objects.get(name="Custom Field Site")
        self.assertTrue(SiteCustomField.objects.filter(site=site, field=field).exists())

        # edit custom field value
        payload = {
            "site": {
                "id": site.id,  # type: ignore
                "client": client.id,  # type: ignore
                "name": "Custom Field Site",
            },
            "custom_fields": [{"field": field.id, "multiple_value": ["one"]}],  # type: ignore
        }
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.assertTrue(
            SiteCustomField.objects.get(site=site, field=field).value,
            ["one"],
        )

        self.check_not_authenticated("put", url)

    def test_delete_site(self):
        from agents.models import Agent

        # setup data
        client = baker.make("clients.Client")
        site_to_delete = baker.make("clients.Site", client=client)
        site_to_move = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site_to_delete)

        # test invalid id
        r = self.client.delete("/clients/500/445/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/sites/{site_to_delete.id}/{site_to_move.id}/"  # type: ignore

        # test deleting with last site under client
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), "A client must have at least 1 site.")

        # test successful deletion
        site_to_move.client = client  # type: ignore
        site_to_move.save(update_fields=["client"])  # type: ignore
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        agent_moved = Agent.objects.get(pk=agent.pk)
        self.assertEqual(agent_moved.site.id, site_to_move.id)  # type: ignore

        self.check_not_authenticated("delete", url)

    def test_get_tree(self):
        # setup data
        baker.make("clients.Site", _quantity=10)
        clients = Client.objects.all()

        url = "/clients/tree/"

        r = self.client.get(url, format="json")
        serializer = ClientTreeSerializer(clients, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_deployments(self):
        # setup data
        deployments = baker.make("clients.Deployment", _quantity=5)

        url = "/clients/deployments/"
        r = self.client.get(url)
        serializer = DeploymentSerializer(deployments, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_add_deployment(self):
        # setup data
        site = baker.make("clients.Site")

        url = "/clients/deployments/"
        payload = {
            "client": site.client.id,  # type: ignore
            "site": site.id,  # type: ignore
            "expires": "2037-11-23 18:53",
            "power": 1,
            "ping": 0,
            "rdp": 1,
            "agenttype": "server",
            "arch": "64",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["site"] = "500"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 404)

        payload["client"] = "500"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("post", url)

    def test_delete_deployment(self):
        # setup data
        deployment = baker.make("clients.Deployment")

        url = "/clients/deployments/"

        url = f"/clients/{deployment.id}/deployment/"  # type: ignore
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Deployment.objects.filter(pk=deployment.id).exists())  # type: ignore

        url = "/clients/32348/deployment/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("delete", url)

    def test_generate_deployment(self):
        # TODO complete this
        url = "/clients/asdkj234kasdasjd-asdkj234-asdk34-sad/deploy/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "invalid")  # type: ignore

        uid = uuid.uuid4()
        url = f"/clients/{uid}/deploy/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
