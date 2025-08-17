import uuid
from itertools import cycle
from unittest.mock import patch

from model_bakery import baker
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from tacticalrmm.constants import CustomFieldModel, CustomFieldType
from tacticalrmm.test import TacticalTestCase

from .models import Client, ClientCustomField, Deployment, Site, SiteCustomField
from .serializers import ClientSerializer, DeploymentSerializer, SiteSerializer

base_url = "/clients"


class TestClientViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_clients(self):
        # setup data
        baker.make("clients.Client", _quantity=5)
        clients = Client.objects.all()  # noqa

        url = f"{base_url}/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 5)

        self.check_not_authenticated("get", url)

    def test_add_client(self):
        url = f"{base_url}/"

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
            "companyname": "TestCo Inc.",
            "initialsetup": True,
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        # test add with custom fields
        field = baker.make(
            "core.CustomField", model=CustomFieldModel.CLIENT, type=CustomFieldType.TEXT
        )
        payload = {
            "client": {"name": "Custom Field Client"},
            "site": {"name": "Setup  Site"},
            "custom_fields": [{"field": field.id, "string_value": "new Value"}],
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

        url = f"{base_url}/{client.id}/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_edit_client(self):
        # setup data
        client = baker.make("clients.Client", name="OldClientName")

        # test invalid id
        r = self.client.put(f"{base_url}/500/", format="json")
        self.assertEqual(r.status_code, 404)

        # test successfull edit client
        data = {"client": {"name": "NewClientName"}, "custom_fields": []}
        url = f"{base_url}/{client.id}/"
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Client.objects.filter(name="NewClientName").exists())
        self.assertFalse(Client.objects.filter(name="OldClientName").exists())

        # test edit client with | in name
        data = {"client": {"name": "NewClie|ntName"}, "custom_fields": []}
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        # test add with custom fields new value
        field = baker.make(
            "core.CustomField",
            model=CustomFieldModel.CLIENT,
            type=CustomFieldType.CHECKBOX,
        )
        payload = {
            "client": {
                "id": client.id,
                "name": "Custom Field Client",
            },
            "custom_fields": [{"field": field.id, "bool_value": True}],
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
                "id": client.id,
                "name": "Custom Field Client",
            },
            "custom_fields": [{"field": field.id, "bool_value": False}],
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
        r = self.client.delete(f"{base_url}/334/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/{client_to_delete.id}/?site_to_move={site_to_move.id}"

        # test successful deletion
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        agent_moved = Agent.objects.get(pk=agent.pk)
        self.assertEqual(agent_moved.site.id, site_to_move.id)
        self.assertFalse(Client.objects.filter(pk=client_to_delete.id).exists())

        self.check_not_authenticated("delete", url)

    def test_get_sites(self):
        # setup data
        baker.make("clients.Site", _quantity=5)
        sites = Site.objects.all()

        url = f"{base_url}/sites/"
        r = self.client.get(url, format="json")
        serializer = SiteSerializer(sites, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_site(self):
        # setup data
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)

        url = f"{base_url}/sites/"

        # test success add
        payload = {
            "site": {"client": client.id, "name": "LA Office"},
            "custom_fields": [],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        # test with | symbol
        payload = {
            "site": {"client": client.id, "name": "LA Office  |*&@#$"},
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
            "site": {"client": site.client.id, "name": "LA Office"},
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
            model=CustomFieldModel.SITE,
            type=CustomFieldType.SINGLE,
            options=["one", "two", "three"],
        )
        payload = {
            "site": {"client": client.id, "name": "Custom Field Site"},
            "custom_fields": [{"field": field.id, "string_value": "one"}],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        site = Site.objects.get(name="Custom Field Site")
        self.assertTrue(SiteCustomField.objects.filter(site=site, field=field).exists())

        self.check_not_authenticated("post", url)

    def test_get_site(self):
        # setup data
        site = baker.make("clients.Site")

        url = f"{base_url}/sites/{site.id}/"
        r = self.client.get(url, format="json")
        serializer = SiteSerializer(site)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_edit_site(self):
        # setup data
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)

        # test invalid id
        r = self.client.put(f"{base_url}/sites/688/", format="json")
        self.assertEqual(r.status_code, 404)

        data = {
            "site": {"client": client.id, "name": "New Site Name"},
            "custom_fields": [],
        }

        url = f"{base_url}/sites/{site.id}/"
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            Site.objects.filter(client=client, name="New Site Name").exists()
        )

        # test add with custom fields new value
        field = baker.make(
            "core.CustomField",
            model=CustomFieldModel.SITE,
            type=CustomFieldType.MULTIPLE,
            options=["one", "two", "three"],
        )
        payload = {
            "site": {
                "id": site.id,
                "client": site.client.id,
                "name": "Custom Field Site",
            },
            "custom_fields": [{"field": field.id, "multiple_value": ["two", "three"]}],
        }
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        site = Site.objects.get(name="Custom Field Site")
        self.assertTrue(SiteCustomField.objects.filter(site=site, field=field).exists())

        # edit custom field value
        payload = {
            "site": {
                "id": site.id,
                "client": client.id,
                "name": "Custom Field Site",
            },
            "custom_fields": [{"field": field.id, "multiple_value": ["one"]}],
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
        r = self.client.delete("{base_url}/500/", format="json")
        self.assertEqual(r.status_code, 404)

        url = f"/clients/sites/{site_to_delete.id}/?move_to_site={site_to_move.id}"

        # test deleting with last site under client
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), "A client must have at least 1 site.")

        # test successful deletion
        site_to_move.client = client
        site_to_move.save(update_fields=["client"])
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        agent_moved = Agent.objects.get(pk=agent.pk)
        self.assertEqual(agent_moved.site.id, site_to_move.id)

        self.check_not_authenticated("delete", url)

    def test_get_deployments(self):
        # setup data
        deployments = baker.make("clients.Deployment", _quantity=5)

        url = f"{base_url}/deployments/"
        r = self.client.get(url)
        serializer = DeploymentSerializer(deployments, many=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_deployment(self):
        # setup data
        site = baker.make("clients.Site")

        url = f"{base_url}/deployments/"
        payload = {
            "client": site.client.id,
            "site": site.id,
            "expires": "2037-11-23T18:53:04-04:00",
            "power": 1,
            "ping": 0,
            "rdp": 1,
            "agenttype": "server",
            "goarch": "amd64",
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

        url = f"{base_url}/deployments/{deployment.id}/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Deployment.objects.filter(pk=deployment.id).exists())

        url = f"{base_url}/deployments/32348/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("delete", url)

    @patch("tacticalrmm.utils.generate_winagent_exe", return_value=Response("ok"))
    def test_generate_deployment(self, post):
        url = "/clients/asdkj234kasdasjd-asdkj234-asdk34-sad/deploy/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "invalid")

        uid = uuid.uuid4()
        url = f"/clients/{uid}/deploy/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        # test valid download
        deployment = baker.make(
            "clients.Deployment",
            install_flags={"rdp": True, "ping": False, "power": False},
        )

        url = f"/clients/{deployment.uid}/deploy/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)


class TestClientPermissions(TacticalTestCase):
    def setUp(self):
        self.setup_client()
        self.setup_coresettings()

    def test_get_clients_permissions(self):
        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        url = f"{base_url}/"

        clients = baker.make("clients.Client", _quantity=5)

        # test getting all clients

        # user with empty role should fail
        self.check_not_authorized("get", url)

        # add can_list_agents roles and should succeed
        user.role.can_list_clients = True
        user.role.save()

        # all agents should be returned
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 5)

        # limit user to specific client. only 1 client should be returned
        user.role.can_view_clients.set([clients[3]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 1)

        # 2 should be returned now
        user.role.can_view_clients.set([clients[0], clients[1]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 2)

        # limit to a specific site. The site shouldn't be in client returned sites
        sites = baker.make("clients.Site", client=clients[4], _quantity=3)
        baker.make("clients.Site", client=clients[0], _quantity=4)
        baker.make("clients.Site", client=clients[1], _quantity=5)

        user.role.can_view_sites.set([sites[0]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 3)
        for client in response.data:
            if client["id"] == clients[0].id:
                self.assertEqual(len(client["sites"]), 4)
            elif client["id"] == clients[1].id:
                self.assertEqual(len(client["sites"]), 5)
            elif client["id"] == clients[4].id:
                self.assertEqual(len(client["sites"]), 1)

        # make sure superusers work
        self.check_authorized_superuser("get", url)

    @patch("clients.models.Client.save")
    @patch("clients.models.Client.delete")
    def test_add_clients_permissions(self, save, delete):
        data = {"client": {"name": "Client Name"}, "site": {"name": "Site Name"}}

        url = f"{base_url}/"

        # test superuser access
        self.check_authorized_superuser("post", url, data)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("post", url, data)

        # add user to role and test
        user.role.can_manage_clients = True
        user.role.save()

        self.check_authorized("post", url, data)

    @patch("clients.models.Client.delete")
    def test_get_edit_delete_clients_permissions(self, delete):
        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        client = baker.make("clients.Client")
        unauthorized_client = baker.make("clients.Client")

        methods = ["get", "put", "delete"]
        url = f"{base_url}/{client.id}/"

        # test user with no roles
        for method in methods:
            self.check_not_authorized(method, url)

        # add correct roles for view edit and delete
        user.role.can_list_clients = True
        user.role.can_manage_clients = True
        user.role.save()

        for method in methods:
            self.check_authorized(method, url)

        # test limiting users to clients and sites

        # limit to client
        user.role.can_view_clients.set([client])

        for method in methods:
            self.check_not_authorized(method, f"{base_url}/{unauthorized_client.id}/")
            self.check_authorized(method, url)

        # make sure superusers work
        for method in methods:
            self.check_authorized_superuser(
                method, f"{base_url}/{unauthorized_client.id}/"
            )

    def test_get_sites_permissions(self):
        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        url = f"{base_url}/sites/"

        clients = baker.make("clients.Client", _quantity=3)
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=10)

        # test getting all sites

        # user with empty role should fail
        self.check_not_authorized("get", url)

        # add can_list_sites roles and should succeed
        user.role.can_list_sites = True
        user.role.save()

        # all sites should be returned
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 10)

        # limit user to specific site. only 1 site should be returned
        user.role.can_view_sites.set([sites[3]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 1)

        # 2 should be returned now
        user.role.can_view_sites.set([sites[0], sites[1]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 2)

        # check if limiting user to client works
        user.role.can_view_sites.clear()
        user.role.can_view_clients.set([clients[0]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 4)

        # add a site to see if the results still work
        user.role.can_view_sites.set([sites[1], sites[0]])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 5)

        # make sure superusers work
        self.check_authorized_superuser("get", url)

    @patch("clients.models.Site.save")
    @patch("clients.models.Site.delete")
    def test_add_sites_permissions(self, delete, save):
        client = baker.make("clients.Client")
        unauthorized_client = baker.make("clients.Client")
        data = {"client": client.id, "name": "Site Name"}

        url = f"{base_url}/sites/"

        # test superuser access
        self.check_authorized_superuser("post", url, data)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("post", url, data)

        # add user to role and test
        user.role.can_manage_sites = True
        user.role.save()

        self.check_authorized("post", url, data)

        # limit to client and test
        user.role.can_view_clients.set([client])
        self.check_authorized("post", url, data)

        # test adding to unauthorized client
        data = {"client": unauthorized_client.id, "name": "Site Name"}
        self.check_not_authorized("post", url, data)

    @patch("clients.models.Site.delete")
    def test_get_edit_delete_sites_permissions(self, delete):
        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        site = baker.make("clients.Site")
        unauthorized_site = baker.make("clients.Site")

        methods = ["get", "put", "delete"]
        url = f"{base_url}/sites/{site.id}/"

        # test user with no roles
        for method in methods:
            self.check_not_authorized(method, url)

        # add correct roles for view edit and delete
        user.role.can_list_sites = True
        user.role.can_manage_sites = True
        user.role.save()

        for method in methods:
            self.check_authorized(method, url)

        # test limiting users to clients and sites

        # limit to site
        user.role.can_view_sites.set([site])

        for method in methods:
            self.check_not_authorized(method, f"{base_url}/{unauthorized_site.id}/")
            self.check_authorized(method, url)

        # test limit to only client
        user.role.can_view_sites.clear()
        user.role.can_view_clients.set([site.client])

        for method in methods:
            self.check_not_authorized(method, f"{base_url}/{unauthorized_site.id}/")
            self.check_authorized(method, url)

        # make sure superusers work
        for method in methods:
            self.check_authorized_superuser(
                method, f"{base_url}/{unauthorized_site.id}/"
            )

    def test_get_pendingactions_permissions(self):
        url = f"{base_url}/deployments/"

        site = baker.make("clients.Site")
        other_site = baker.make("clients.Site")
        deployments = baker.make("clients.Deployment", site=site, _quantity=5)  # noqa
        other_deployments = baker.make(  # noqa
            "clients.Deployment", site=other_site, _quantity=7
        )

        # test getting all deployments
        # make sure superusers work
        self.check_authorized_superuser("get", url)

        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # user with empty role should fail
        self.check_not_authorized("get", url)

        # add can_list_sites roles and should succeed
        user.role.can_list_deployments = True
        user.role.save()

        # all sites should be returned
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 12)

        # limit user to specific site. only 1 site should be returned
        user.role.can_view_sites.set([site])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 5)

        # all should be returned now
        user.role.can_view_clients.set([other_site.client])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 12)

        # check if limiting user to client works
        user.role.can_view_sites.clear()
        user.role.can_view_clients.set([other_site.client])
        response = self.check_authorized("get", url)
        self.assertEqual(len(response.data), 7)

    @patch("clients.models.Deployment.save")
    def test_add_deployments_permissions(self, save):
        site = baker.make("clients.Site")
        unauthorized_site = baker.make("clients.Site")
        data = {
            "site": site.id,
        }

        # test adding to unauthorized client
        unauthorized_data = {
            "site": unauthorized_site.id,
        }

        url = f"{base_url}/deployments/"

        # test superuser access
        self.check_authorized_superuser("post", url, data)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("post", url, data)

        # add user to role and test
        user.role.can_manage_deployments = True
        user.role.save()

        self.check_authorized("post", url, data)

        # limit to client and test
        user.role.can_view_clients.set([site.client])
        self.check_authorized("post", url, data)
        self.check_not_authorized("post", url, unauthorized_data)

        # limit to site and test
        user.role.can_view_clients.clear()
        user.role.can_view_sites.set([site])
        self.check_authorized("post", url, data)
        self.check_not_authorized("post", url, unauthorized_data)

    @patch("clients.models.Deployment.delete")
    def test_delete_deployments_permissions(self, delete):
        site = baker.make("clients.Site")
        unauthorized_site = baker.make("clients.Site")
        deployment = baker.make("clients.Deployment", site=site)
        unauthorized_deployment = baker.make(
            "clients.Deployment", site=unauthorized_site
        )

        url = f"{base_url}/deployments/{deployment.id}/"
        unauthorized_url = f"{base_url}/deployments/{unauthorized_deployment.id}/"

        # make sure superusers work
        self.check_authorized_superuser("delete", url)
        self.check_authorized_superuser("delete", unauthorized_url)

        # create user with empty role
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # make sure user with empty role is unauthorized
        self.check_not_authorized("delete", url)
        self.check_not_authorized("delete", unauthorized_url)

        # add correct roles for view edit and delete
        user.role.can_manage_deployments = True
        user.role.save()

        self.check_authorized("delete", url)
        self.check_authorized("delete", unauthorized_url)

        # test limiting users to clients and sites

        # limit to site
        user.role.can_view_sites.set([site])

        # recreate deployment since it is being deleted even though I am mocking delete on Deployment model???
        unauthorized_deployment = baker.make(
            "clients.Deployment", site=unauthorized_site
        )
        unauthorized_url = f"{base_url}/deployments/{unauthorized_deployment.id}/"

        self.check_authorized("delete", url)
        self.check_not_authorized("delete", unauthorized_url)

        # test limit to only client
        user.role.can_view_sites.clear()
        user.role.can_view_clients.set([site.client])

        self.check_authorized("delete", url)
        self.check_not_authorized("delete", unauthorized_url)

    def test_restricted_user_creating_clients(self):
        from accounts.models import User

        # when a user that is limited to a specific subset of clients creates a client. It should allow access to that client
        client = baker.make("clients.Client")
        user = self.create_user_with_roles(["can_manage_clients"])
        self.client.force_authenticate(user=user)
        user.role.can_view_clients.set([client])

        data = {"client": {"name": "New Client"}, "site": {"name": "New Site"}}

        self.client.post(f"{base_url}/", data, format="json")

        # make sure two clients are allowed now
        self.assertEqual(User.objects.get(id=user.pk).role.can_view_clients.count(), 2)

    def test_restricted_user_creating_sites(self):
        from accounts.models import User

        # when a user that is limited to a specific subset of clients creates a client. It should allow access to that client
        site = baker.make("clients.Site")
        user = self.create_user_with_roles(["can_manage_sites"])
        self.client.force_authenticate(user=user)
        user.role.can_view_sites.set([site])

        data = {"site": {"client": site.client.id, "name": "New Site"}}

        self.client.post(f"{base_url}/sites/", data, format="json")

        # make sure two sites are allowed now
        self.assertEqual(User.objects.get(id=user.pk).role.can_view_sites.count(), 2)
