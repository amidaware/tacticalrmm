from itertools import cycle
from unittest.mock import patch

from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import WinUpdate
from .serializers import UpdateSerializer


class TestWinUpdateViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_run_update_scan(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        url = f"/winupdate/{agent.pk}/runupdatescan/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "getwinupdates"}, wait=False)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_install_updates(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdate", agent=agent, _quantity=4)
        baker.make("winupdate.WinUpdatePolicy", agent=agent)
        url = f"/winupdate/{agent.pk}/installnow/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_once()

        self.check_not_authenticated("get", url)

    def test_get_winupdates(self):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdate", agent=agent, _quantity=4)

        # test a call where agent doesn't exist
        resp = self.client.get("/winupdate/500/getwinupdates/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/winupdate/{agent.pk}/getwinupdates/"
        resp = self.client.get(url, format="json")
        serializer = UpdateSerializer(agent)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["winupdates"]), 4)  # type: ignore
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    """ @patch("winupdate.tasks.check_for_updates_task.apply_async")
    def test_run_update_scan(self, mock_task):

        # test a call where agent doesn't exist
        resp = self.client.get("/winupdate/500/runupdatescan/", format="json")
        self.assertEqual(resp.status_code, 404)

        agent = baker.make_recipe("agents.agent")
        url = f"/winupdate/{agent.pk}/runupdatescan/"

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_task.assert_called_with(
            queue="wupdate",
            kwargs={"pk": agent.pk, "wait": False, "auto_approve": True},
        )

        self.check_not_authenticated("get", url) """

    """ @patch("agents.models.Agent.salt_api_cmd")
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
        mock_cmd.return_value = {}
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 400)

        # test agent command success
        mock_cmd.return_value = {"pid": 3316}
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("get", url) """

    def test_edit_policy(self):
        url = "/winupdate/editpolicy/"
        agent = baker.make_recipe("agents.agent")
        winupdate = baker.make("winupdate.WinUpdate", agent=agent)

        invalid_data = {"pk": 500, "policy": "inherit"}
        # test a call where winupdate doesn't exist
        resp = self.client.patch(url, invalid_data, format="json")
        self.assertEqual(resp.status_code, 404)

        data = {"pk": winupdate.pk, "policy": "inherit"}  # type: ignore

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("patch", url)


class WinupdateTasks(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

        site = baker.make("clients.Site")
        self.online_agents = baker.make_recipe(
            "agents.online_agent", site=site, _quantity=2
        )
        self.offline_agent = baker.make_recipe("agents.agent", site=site)

    @patch("agents.models.Agent.nats_cmd")
    @patch("time.sleep")
    def test_auto_approve_task(self, mock_sleep, nats_cmd):
        from .tasks import auto_approve_updates_task

        # Setup data
        baker.make_recipe(
            "winupdate.winupdate",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=20,
        )
        baker.make_recipe(
            "winupdate.winupdate_approve",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=3,
        )

        # run task synchronously
        auto_approve_updates_task()

        # make sure the check_for_updates_task was run once for each online agent
        self.assertEqual(nats_cmd.call_count, 2)

        # check if all of the created updates were approved
        winupdates = WinUpdate.objects.all()
        for update in winupdates:
            self.assertEqual(update.action, "approve")

    """ @patch("agents.models.Agent.salt_api_async")
    def test_check_agent_update_daily_schedule(self, agent_salt_cmd):
        from .tasks import check_agent_update_schedule_task

        # Setup data
        # create an online agent with auto approval turned off
        agent = baker.make_recipe("agents.online_agent")
        baker.make("winupdate.WinUpdatePolicy", agent=agent)

        # create approved winupdates
        baker.make_recipe(
            "winupdate.approved_winupdate",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=20,
        )

        # create daily patch policy schedules for the agents
        winupdate_policy = baker.make_recipe(
            "winupdate.winupdate_approve",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=3,
        )

        check_agent_update_schedule_task()
        agent_salt_cmd.assert_called_with(func="win_agent.install_updates")
        self.assertEquals(agent_salt_cmd.call_count, 2) """

    """ @patch("agents.models.Agent.salt_api_async")
    def test_check_agent_update_monthly_schedule(self, agent_salt_cmd):
        from .tasks import check_agent_update_schedule_task

        # Setup data
        # create an online agent with auto approval turned off
        agent = baker.make_recipe("agents.online_agent")
        baker.make("winupdate.WinUpdatePolicy", agent=agent)

        # create approved winupdates
        baker.make_recipe(
            "winupdate.approved_winupdate",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=20,
        )

        # create monthly patch policy schedules for the agents
        winupdate_policy = baker.make_recipe(
            "winupdate.winupdate_approve_monthly",
            agent=cycle(
                [self.online_agents[0], self.online_agents[1], self.offline_agent]
            ),
            _quantity=3,
        )

        check_agent_update_schedule_task()
        agent_salt_cmd.assert_called_with(func="win_agent.install_updates")
        self.assertEquals(agent_salt_cmd.call_count, 2) """
