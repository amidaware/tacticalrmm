from tacticalrmm.test import TacticalTestCase
from .serializers import UpdateSerializer, WinUpdateSerializer, ApprovedUpdateSerializer
from model_bakery import baker
from model_bakery.recipe import foreign_key
from unittest.mock import patch
from pprint import pprint


class TestWinUpdateViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_winupdates(self):

        agent = baker.make_recipe("agents.agent")
        winupdates = baker.make("winupdate.WinUpdate", agent=agent, _quantity=4)

        # test a call where agent doesn't exist
        resp = self.client.get("/winupdate/500/getwinupdates/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/winupdate/{agent.pk}/getwinupdates/"
        resp = self.client.get(url, format="json")
        serializer = UpdateSerializer(agent)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["winupdates"]), 4)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    @patch("winupdate.tasks.check_for_updates_task.apply_async")
    def test_run_update_scan(self, mock_task):

        # test a call where agent doesn't exist
        resp = self.client.get("/winupdate/500/runupdatescan/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"/winupdate/{agent.pk}/runupdatescan/"

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_task.assert_called_with(
            queue="wupdate", kwargs={"pk": agent.pk, "wait": False}
        )

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_install_updates(self, mock_cmd):

        # test a call where agent doesn't exist
        resp = self.client.get("/winupdate/500/installnow/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"/winupdate/{agent.pk}/installnow/"

        # test agent command timeout
        mock_cmd.return_value = "timeout"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)

        # test agent command error
        mock_cmd.return_value = "error"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)

        # test agent command running
        mock_cmd.return_value = "running"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)

        # can't get this to work right
        # test agent command no pid field
        #mock_cmd.return_value = ""
        #resp = self.client.get(url, format="json")
        #self.assertEqual(resp.status_code, 400)

        # test agent command success
        # mock_cmd.return_value = {"pid", 3316}
        # resp = self.client.get(url, format="json")
        # self.assertEqual(resp.status_code, 200)

    def test_edit_policy(self):
        url = "/winupdate/editpolicy/"
        winupdate = baker.make("winupdate.WinUpdate")

        invalid_data = {"pk": 500, "policy": "inherit"}
        # test a call where winupdate doesn't exist
        resp = self.client.patch(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        data = {"pk": winupdate.pk, "policy": "inherit"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

# TODO: add agent api to test