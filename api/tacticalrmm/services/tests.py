from tacticalrmm.test import TacticalTestCase
from model_bakery import baker
from unittest.mock import patch
from .serializers import ServicesSerializer
from agents.models import Agent


class TestServiceViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()

    def test_get_services(self):

        # test a call where agent doesn't exist
        resp = self.client.get("/services/500/services/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")
        url = f"/services/{agent.pk}/services/"
        serializer = ServicesSerializer(agent)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)

        self.check_not_authenticated("get", url)

    def test_default_services(self):
        url = "/services/defaultservices/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(type(resp.data), list)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_get_refreshed_services(self, salt_api_cmd):
        # test a call where agent doesn't exist
        resp = self.client.get("/services/500/refreshedservices/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")
        url = f"/services/{agent.pk}/refreshedservices/"

        salt_return = [
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
        salt_api_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(timeout=15, func="win_agent.get_services")
        salt_api_cmd.reset_mock()

        # test failed attempt
        salt_api_cmd.return_value = "error"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(timeout=15, func="win_agent.get_services")
        salt_api_cmd.reset_mock()

        # test successful attempt
        salt_api_cmd.return_value = salt_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(timeout=15, func="win_agent.get_services")
        self.assertEquals(Agent.objects.get(pk=agent.pk).services, salt_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_service_action(self, salt_api_cmd):
        url = "/services/serviceaction/"

        invalid_data = {"pk": 500, "sv_name": "AeLookupSvc", "sv_action": "restart"}
        # test a call where agent doesn't exist
        resp = self.client.post(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent_with_services")

        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "sv_action": "restart"}

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=45,
            func=f"service.restart",
            arg="AeLookupSvc",
        )
        salt_api_cmd.reset_mock()

        salt_api_cmd.return_value = "error"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=45,
            func=f"service.restart",
            arg="AeLookupSvc",
        )
        salt_api_cmd.reset_mock()

        # test successful attempt
        salt_api_cmd.return_value = True
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=45,
            func=f"service.restart",
            arg="AeLookupSvc",
        )

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_service_detail(self, salt_api_cmd):
        # test a call where agent doesn't exist
        resp = self.client.get(
            "/services/500/doesntexist/servicedetail/", format="json"
        )
        self.assertEqual(resp.status_code, 404)

        salt_return = {
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
        salt_api_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(timeout=20, func="service.info", arg="alg")
        salt_api_cmd.reset_mock()

        salt_api_cmd.return_value = "error"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(timeout=20, func="service.info", arg="alg")
        salt_api_cmd.reset_mock()

        # test successful attempt
        salt_api_cmd.return_value = salt_return
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(timeout=20, func="service.info", arg="alg")
        self.assertEquals(resp.data, salt_return)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_edit_service(self, salt_api_cmd):
        url = "/services/editservice/"
        agent = baker.make_recipe("agents.agent_with_services")

        invalid_data = {"pk": 500, "sv_name": "AeLookupSvc", "edit_action": "autodelay"}
        # test a call where agent doesn't exist
        resp = self.client.post(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "autodelay"}

        # test failed attempt
        salt_api_cmd.return_value = "timeout"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="service.modify",
            arg=data["sv_name"],
            kwargs={"start_type": "auto", "start_delayed": True},
        )
        salt_api_cmd.reset_mock()

        salt_api_cmd.return_value = "error"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="service.modify",
            arg=data["sv_name"],
            kwargs={"start_type": "auto", "start_delayed": True},
        )
        salt_api_cmd.reset_mock()

        # test successful attempt autodelay
        salt_api_cmd.return_value = True
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="service.modify",
            arg=data["sv_name"],
            kwargs={"start_type": "auto", "start_delayed": True},
        )
        salt_api_cmd.reset_mock()

        # test successful attempt with auto
        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "auto"}
        salt_api_cmd.return_value = True
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="service.modify",
            arg=data["sv_name"],
            kwargs={"start_type": "auto", "start_delayed": False},
        )
        salt_api_cmd.reset_mock()

        # test successful attempt with manual
        data = {"pk": agent.pk, "sv_name": "AeLookupSvc", "edit_action": "manual"}
        salt_api_cmd.return_value = True
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="service.modify",
            arg=data["sv_name"],
            kwargs={"start_type": "manual"},
        )

        self.check_not_authenticated("post", url)
