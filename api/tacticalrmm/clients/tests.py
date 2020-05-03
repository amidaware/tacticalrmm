from tacticalrmm.test import BaseTestCase
from unittest import mock

from .models import Client, Site


class TestClientViews(BaseTestCase):
    def test_initial_setup(self):
        url = "/clients/initialsetup/"

        payload = {"client": "Amazon", "site": "NY Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload = {"client": "Amaz|on", "site": "NY Off|ice  |*&@#$"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_add_client(self):
        url = "/clients/addclient/"

        payload = {"client": "Amazon", "site": "NY Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload = {"client": "Amaz|on", "site": "NY Off|ice  |*&@#$"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {"client": "Google", "site": "NY Office"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

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

    def test_installer_list_clients(self):
        url = "/clients/installer/listclients/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

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

    def test_installer_list_sites(self):
        url = "/clients/installer/Google/sites/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)
