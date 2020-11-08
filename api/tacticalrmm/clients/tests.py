import uuid
from tacticalrmm.test import TacticalTestCase
from model_bakery import baker
from .models import Client, Site, Deployment
from rest_framework.serializers import ValidationError

from .serializers import (
    ClientSerializer,
    SiteSerializer,
    ClientTreeSerializer,
    DeploymentSerializer,
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
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_client(self):
        url = "/clients/clients/"
        payload = {"client": "Company 1", "site": "Site 1"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["client"] = "Company1|askd"
        serializer = ClientSerializer(data={"name": payload["client"]}, context=payload)
        with self.assertRaisesMessage(
            ValidationError, "Client name cannot contain the | character"
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {"client": "Company 156", "site": "Site2|a34"}
        serializer = ClientSerializer(data={"name": payload["client"]}, context=payload)
        with self.assertRaisesMessage(
            ValidationError, "Site name cannot contain the | character"
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test unique
        payload = {"client": "Company 1", "site": "Site 1"}
        serializer = ClientSerializer(data={"name": payload["client"]}, context=payload)
        with self.assertRaisesMessage(
            ValidationError, "client with this name already exists."
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test long site name
        payload = {"client": "Company 2394", "site": "Site123" * 100}
        serializer = ClientSerializer(data={"name": payload["client"]}, context=payload)
        with self.assertRaisesMessage(ValidationError, "Site name too long"):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {
            "client": {"client": "Company 4", "site": "HQ"},
            "initialsetup": True,
            "timezone": "America/Los_Angeles",
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_edit_client(self):
        # setup data
        client = baker.make("clients.Client")

        # test invalid id
        r = self.client.put("/clients/500/client/", format="json")
        self.assertEqual(r.status_code, 404)

        data = {"id": client.id, "name": "New Name"}

        url = f"/clients/{client.id}/client/"
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Client.objects.filter(name="New Name").exists())

        self.check_not_authenticated("put", url)

    def test_delete_client(self):
        # setup data
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)
        agent = baker.make_recipe("agents.agent", site=site)

        # test invalid id
        r = self.client.delete("/clients/500/client/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/{client.id}/client/"

        # test deleting with agents under client
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 400)

        # test successful deletion
        agent.delete()
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Client.objects.filter(pk=client.id).exists())
        self.assertFalse(Site.objects.filter(pk=site.id).exists())

        self.check_not_authenticated("put", url)

    def test_get_sites(self):
        # setup data
        baker.make("clients.Site", _quantity=5)
        sites = Site.objects.all()

        url = "/clients/sites/"
        r = self.client.get(url, format="json")
        serializer = SiteSerializer(sites, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_site(self):
        # setup data
        site = baker.make("clients.Site")

        url = "/clients/sites/"

        # test success add
        payload = {"client": site.client.id, "name": "LA Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            Site.objects.filter(
                name="LA Office", client__name=site.client.name
            ).exists()
        )

        # test with | symbol
        payload = {"client": site.client.id, "name": "LA Off|ice  |*&@#$"}
        serializer = SiteSerializer(data=payload, context={"clientpk": site.client.id})
        with self.assertRaisesMessage(
            ValidationError, "Site name cannot contain the | character"
        ):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test site already exists
        payload = {"client": site.client.id, "name": "LA Office"}
        serializer = SiteSerializer(data=payload, context={"clientpk": site.client.id})
        with self.assertRaisesMessage(ValidationError, "Site LA Office already exists"):
            self.assertFalse(serializer.is_valid(raise_exception=True))

        self.check_not_authenticated("post", url)

    def test_edit_site(self):
        # setup data
        site = baker.make("clients.Site")

        # test invalid id
        r = self.client.put("/clients/500/site/", format="json")
        self.assertEqual(r.status_code, 404)

        data = {"id": site.id, "name": "New Name", "client": site.client.id}

        url = f"/clients/{site.id}/site/"
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Site.objects.filter(name="New Name").exists())

        self.check_not_authenticated("put", url)

    def test_delete_site(self):
        # setup data
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site)

        # test invalid id
        r = self.client.delete("/clients/500/site/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/{site.id}/site/"

        # test deleting with last site under client
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 400)

        # test deletion when agents exist under site
        baker.make("clients.Site", client=site.client)
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 400)

        # test successful deletion
        agent.delete()
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Site.objects.filter(pk=site.id).exists())

        self.check_not_authenticated("delete", url)

    def test_get_tree(self):
        # setup data
        baker.make("clients.Site", _quantity=10)
        clients = Client.objects.all()

        url = "/clients/tree/"

        r = self.client.get(url, format="json")
        serializer = ClientTreeSerializer(clients, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_get_deployments(self):
        # setup data
        deployments = baker.make("clients.Deployment", _quantity=5)

        url = "/clients/deployments/"
        r = self.client.get(url)
        serializer = DeploymentSerializer(deployments, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_deployment(self):
        # setup data
        site = baker.make("clients.Site")

        url = "/clients/deployments/"
        payload = {
            "client": site.client.id,
            "site": site.id,
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

        url = f"/clients/{deployment.id}/deployment/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Deployment.objects.filter(pk=deployment.id).exists())

        url = "/clients/32348/deployment/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("delete", url)

    def test_generate_deployment(self):
        # TODO complete this
        url = "/clients/asdkj234kasdasjd-asdkj234-asdk34-sad/deploy/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "invalid")

        uid = uuid.uuid4()
        url = f"/clients/{uid}/deploy/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
