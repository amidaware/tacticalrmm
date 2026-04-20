from unittest.mock import patch

from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import WinUpdate
from .serializers import WinUpdateSerializer

base_url = "/winupdate"


class TestWinUpdateViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_run_update_scan(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        url = f"{base_url}/{agent.agent_id}/scan/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "getwinupdates"}, wait=False)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_install_updates(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdate", agent=agent, _quantity=4)
        baker.make("winupdate.WinUpdatePolicy", agent=agent)
        url = f"{base_url}/{agent.agent_id}/install/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_once()

        self.check_not_authenticated("post", url)

    def test_get_winupdates(self):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdate", agent=agent, _quantity=4)

        # test a call where agent doesn't exist
        resp = self.client.get(f"{base_url}/234kj34lk/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"{base_url}/{agent.agent_id}/"
        resp = self.client.get(url, format="json")
        updates = WinUpdate.objects.filter(agent=agent).order_by("-id", "installed")
        serializer = WinUpdateSerializer(updates, many=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_edit_winupdate(self):
        agent = baker.make_recipe("agents.agent")
        winupdate = baker.make("winupdate.WinUpdate", agent=agent)
        url = f"{base_url}/{winupdate.pk}/"

        data = {"policy": "inherit"}
        # test a call where winupdate doesn't exist
        resp = self.client.put(f"{base_url}/500/", data, format="json")
        self.assertEqual(resp.status_code, 404)

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("put", url)


class TestWinUpdatePermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()

    @patch("agents.models.Agent.nats_cmd", return_value="ok")
    def test_get_scan_install_permissions(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdatePolicy", agent=agent)
        unauthorized_agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdatePolicy", agent=unauthorized_agent)
        baker.make("winupdate.WinUpdate", agent=agent)
        baker.make("winupdate.WinUpdate", agent=unauthorized_agent)

        test_data = [
            {"url": f"{base_url}/{agent.agent_id}/", "method": "get"},
            {"url": f"{base_url}/{agent.agent_id}/scan/", "method": "post"},
            {"url": f"{base_url}/{agent.agent_id}/install/", "method": "post"},
        ]

        for data in test_data:
            # test superuser
            self.check_authorized_superuser(data["method"], data["url"])

            # test user with no roles
            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

            self.check_not_authorized(data["method"], data["url"])

            # test with correct role
            user.role.can_manage_winupdates = True
            user.role.save()

            self.check_authorized(data["method"], data["url"])

            # test limiting user to site
            user.role.can_view_sites.set([agent.site])
            self.check_authorized(data["method"], data["url"])

            user.role.can_view_sites.set([unauthorized_agent.site])
            self.check_not_authorized(data["method"], data["url"])

            self.client.logout()

    def test_edit_winupdate_permissions(self):
        agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdatePolicy", agent=agent)
        update = baker.make("winupdate.WinUpdate", agent=agent)

        unauthorized_agent = baker.make_recipe("agents.agent")
        baker.make("winupdate.WinUpdatePolicy", agent=unauthorized_agent)
        baker.make("winupdate.WinUpdate", agent=unauthorized_agent)

        url = f"{base_url}/{update.pk}/"

        # test superuser
        self.check_authorized_superuser("put", url)

        # test user with no roles
        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        self.check_not_authorized("put", url)

        # test with correct role
        user.role.can_manage_winupdates = True
        user.role.save()

        self.check_authorized("put", url)

        # test limiting user to site
        user.role.can_view_sites.set([agent.site])
        self.check_authorized("put", url)

        user.role.can_view_sites.set([unauthorized_agent.site])
        self.check_not_authorized("put", url)
