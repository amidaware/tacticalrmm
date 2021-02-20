from unittest.mock import patch

from model_bakery import baker

from agents.models import Agent
from tacticalrmm.test import TacticalTestCase


class TestServiceViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_default_services(self):
        url = "/services/defaultservices/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(type(resp.data), list)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_get_services(self, nats_cmd):
        # test a call where agent doesn't exist
        resp = self.client.get("/services/500/services/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")
        url = f"/services/{agent.pk}/services/"

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
        self.assertEquals(Agent.objects.get(pk=agent.pk).services, nats_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_service_action(self, nats_cmd):
        url = "/services/serviceaction/"

        invalid_data = {"pk": 500, "sv_name": "AeLookupSvc", "sv_action": "restart"}
        # test a call where agent doesn't exist
        resp = self.client.post(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")

        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "sv_action": "restart"}

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
            "/services/500/doesntexist/servicedetail/", format="json"
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
        url = f"/services/{agent.pk}/alg/servicedetail/"

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
        self.assertEquals(resp.data, nats_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_edit_service(self, nats_cmd):
        url = "/services/editservice/"
        agent = baker.make_recipe("agents.agent_with_services")

        invalid_data = {"pk": 500, "sv_name": "AeLookupSvc", "edit_action": "autodelay"}
        # test a call where agent doesn't exist
        resp = self.client.post(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "autodelay"}

        # test timeout
        nats_cmd.return_value = "timeout"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.reset_mock()

        # test successful attempt autodelay
        nats_cmd.return_value = {"success": True, "errormsg": ""}
        resp = self.client.post(url, data, format="json")
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
        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "auto"}
        nats_cmd.return_value = {
            "success": False,
            "errormsg": "The parameter is incorrect",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        nats_cmd.reset_mock()

        # test catch all
        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "auto"}
        nats_cmd.return_value = {"success": False, "errormsg": ""}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data, "Something went wrong")

        self.check_not_authenticated("post", url)
