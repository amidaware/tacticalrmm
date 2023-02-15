from unittest.mock import patch

from model_bakery import baker

from agents.models import Agent
from tacticalrmm.test import TacticalTestCase

base_url = "/services"


class TestServiceViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_get_services(self, nats_cmd):
        # test a call where agent doesn't exist
        resp = self.client.get("/services/500234hjk348982h/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")
        url = f"{base_url}/{agent.agent_id}/"

        nats_return = [
            {
                "pid": 880,
                "name": "AeLookupSvc",
                "status": "stopped",
                "binpath": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                "username": "localSystem",
                "start_type": "manual",
                "description": "Processes application compatibility cache requests for applications as they are launched",
                "display_name": "Application Experience",
            },
            {
                "pid": 812,
                "name": "ALG",
                "status": "stopped",
                "binpath": "C:\\Windows\\System32\\alg.exe",
                "username": "NT AUTHORITY\\LocalService",
                "start_type": "manual",
                "description": "Provides support for 3rd party protocol plug-ins for Internet Connection Sharing",
                "display_name": "Application Layer Gateway Service",
            },
        ]

        # test failed attempt
        nats_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.assert_called_with(data={"func": "winservices"}, timeout=10)
        nats_cmd.reset_mock()

        # test successful attempt
        nats_cmd.return_value = nats_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        nats_cmd.assert_called_with(data={"func": "winservices"}, timeout=10)
        self.assertEqual(Agent.objects.get(pk=agent.pk).services, nats_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_service_action(self, nats_cmd):
        data = {"sv_action": "restart"}
        # test a call where agent doesn't exist
        resp = self.client.post(
            f"{base_url}/kjhj4hj4khj34h34j/AeLookupSvc/", data, format="json"
        )
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")
        url = f"/services/{agent.agent_id}/AeLookupSvc/"

        # test failed attempt
        nats_cmd.return_value = "timeout"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.assert_called_with(
            {
                "func": "winsvcaction",
                "payload": {
                    "name": "AeLookupSvc",
                    "action": "stop",
                },
            },
            timeout=32,
        )
        nats_cmd.reset_mock()

        # test successful attempt
        nats_cmd.return_value = {"success": True, "errormsg": ""}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_service_detail(self, nats_cmd):
        # test a call where agent doesn't exist
        resp = self.client.get(
            f"{base_url}/34kjhj3h4jh3kjh34/service_name/", format="json"
        )
        self.assertEqual(resp.status_code, 404)

        nats_return = {
            "pid": 812,
            "name": "ALG",
            "status": "stopped",
            "binpath": "C:\\Windows\\System32\\alg.exe",
            "username": "NT AUTHORITY\\LocalService",
            "start_type": "manual",
            "description": "Provides support for 3rd party protocol plug-ins for Internet Connection Sharing",
            "display_name": "Application Layer Gateway Service",
        }

        agent = baker.make_recipe("agents.agent")
        url = f"{base_url}/{agent.agent_id}/alg/"

        # test failed attempt
        nats_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.assert_called_with(
            {"func": "winsvcdetail", "payload": {"name": "alg"}}, timeout=10
        )
        nats_cmd.reset_mock()

        # test successful attempt
        nats_cmd.return_value = nats_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        nats_cmd.assert_called_with(
            {"func": "winsvcdetail", "payload": {"name": "alg"}}, timeout=10
        )
        self.assertEqual(resp.data, nats_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_edit_service(self, nats_cmd):
        agent = baker.make_recipe("agents.agent_with_services")
        url = f"{base_url}/{agent.agent_id}/AeLookupSvc/"

        data = {"startType": "autodelay"}
        # test a call where agent doesn't exist
        resp = self.client.put(
            f"{base_url}/234kjh2k3hkj23h4kj3h4k3jh/service/", data, format="json"
        )
        self.assertEqual(resp.status_code, 404)

        # test timeout
        nats_cmd.return_value = "timeout"
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.reset_mock()

        # test successful attempt autodelay
        nats_cmd.return_value = {"success": True, "errormsg": ""}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        nats_cmd.assert_called_with(
            {
                "func": "editwinsvc",
                "payload": {
                    "name": "AeLookupSvc",
                    "startType": "autodelay",
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test error message from agent
        data = {"startType": "auto"}
        nats_cmd.return_value = {
            "success": False,
            "errormsg": "The parameter is incorrect",
        }
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.reset_mock()

        # test catch all
        nats_cmd.return_value = {"success": False, "errormsg": ""}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data, "Something went wrong")

        self.check_not_authenticated("put", url)


class TestServicePermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()

    @patch("agents.models.Agent.nats_cmd", return_value="ok")
    def test_services_permissions(self, nats_cmd):
        agent = baker.make_recipe("agents.agent_with_services")
        unauthorized_agent = baker.make_recipe("agents.agent_with_services")

        test_data = [
            {"url": f"{base_url}/{agent.agent_id}/", "method": "get"},
            {"url": f"{base_url}/{agent.agent_id}/service_name/", "method": "get"},
            {"url": f"{base_url}/{agent.agent_id}/service_name/", "method": "post"},
            {"url": f"{base_url}/{agent.agent_id}/service_name/", "method": "put"},
        ]

        for data in test_data:
            # test superuser
            self.check_authorized_superuser(data["method"], data["url"])

            # test user with no roles
            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

            self.check_not_authorized(data["method"], data["url"])

            # test with correct role
            user.role.can_manage_winsvcs = True
            user.role.save()

            self.check_authorized(data["method"], data["url"])

            # test limiting user to client
            user.role.can_view_clients.set([agent.client])
            self.check_authorized(data["method"], data["url"])

            user.role.can_view_clients.set([unauthorized_agent.client])

            self.client.logout()
