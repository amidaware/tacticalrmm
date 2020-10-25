import uuid
from unittest import mock

from tacticalrmm.test import BaseTestCase

from .models import Client, Site, Deployment


class TestClientViews(BaseTestCase):
    def test_get_clients(self):
        url = "/clients/clients/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_add_client(self):
        url = "/clients/clients/"
        payload = {"client": "Company 1", "site": "Site 1"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["client"] = "Company1|askd"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {"client": "Company 1", "site": "Site2|a34"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # test unique
        payload = {"client": "Company 1", "site": "Site 1"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {
            "client": {"client": "Company 4", "site": "HQ"},
            "initialsetup": True,
            "timezone": "America/Los_Angeles",
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

    def test_get_sites(self):
        url = "/clients/sites/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_add_site(self):
        url = "/clients/addsite/"

        payload = {"client": "Google", "site": "LA Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {"client": "Google", "site": "LA Off|ice  |*&@#$"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {"client": "Google", "site": "KN Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_list_clients(self):
        url = "/clients/listclients/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_load_tree(self):

        with mock.patch(
            "clients.models.Client.has_failing_checks",
            new_callable=mock.PropertyMock,
            return_value=True,
        ):

            url = "/clients/loadtree/"

            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)

            client = Client.objects.get(client="Facebook")
            self.assertTrue(f"Facebook|{client.pk}|negative" in r.data.keys())

        with mock.patch(
            "clients.models.Site.has_failing_checks",
            new_callable=mock.PropertyMock,
            return_value=False,
        ):

            client = Client.objects.get(client="Google")
            site = Site.objects.get(client=client, site="LA Office")
            self.assertTrue(
                f"LA Office|{site.pk}|black" in [i for i in r.data.values()][0]
            )

        self.check_not_authenticated("get", url)

    def test_load_clients(self):
        url = "/clients/loadclients/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_get_deployments(self):
        url = "/clients/deployments/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_add_deployment(self):
        url = "/clients/deployments/"
        payload = {
            "client": "Google",
            "site": "Main Office",
            "expires": "2037-11-23 18:53",
            "power": 1,
            "ping": 0,
            "rdp": 1,
            "agenttype": "server",
            "arch": "64",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["site"] = "ASDkjh23k4jh"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 404)

        payload["client"] = "324234ASDqwe"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("post", url)

    def test_delete_deployment(self):
        url = "/clients/deployments/"
        payload = {
            "client": "Google",
            "site": "Main Office",
            "expires": "2037-11-23 18:53",
            "power": 1,
            "ping": 0,
            "rdp": 1,
            "agenttype": "server",
            "arch": "64",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        dep = Deployment.objects.last()
        url = f"/clients/{dep.pk}/deployment/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

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
