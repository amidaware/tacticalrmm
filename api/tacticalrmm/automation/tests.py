from unittest.mock import patch
from tacticalrmm.test import TacticalTestCase
from model_bakery import baker, seq
from itertools import cycle
from agents.models import Agent
from winupdate.models import WinUpdatePolicy

from .serializers import (
    PolicyTableSerializer,
    PolicySerializer,
    AutoTaskPolicySerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
    PolicyCheckSerializer,
    RelatedAgentPolicySerializer,
    RelatedSitePolicySerializer,
    RelatedClientPolicySerializer,
)


class TestPolicyViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def create_policy_checks(self, policy):
        # will create 1 of every check adn associate it with the policy object passed
        check_recipes = [
            "checks.diskspace_check",
            "checks.ping_check",
            "checks.cpuload_check",
            "checks.memory_check",
            "checks.winsvc_check",
            "checks.script_check",
            "checks.eventlog_check",
        ]

        checks = list()
        for recipe in check_recipes:
            checks.append(baker.make_recipe(recipe, policy=policy))

        return checks

    def test_get_all_policies(self):
        url = "/automation/policies/"

        policies = baker.make("automation.Policy", _quantity=3)
        resp = self.client.get(url, format="json")
        serializer = PolicyTableSerializer(policies, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_get_policy(self):
        # returns 404 for invalid policy pk
        resp = self.client.get("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")
        url = f"/automation/policies/{policy.pk}/"

        resp = self.client.get(url, format="json")
        serializer = PolicySerializer(policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_add_policy(self):
        url = "/automation/policies/"

        data = {
            "name": "Test Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # running again should fail since names are unique
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # create policy with tasks and checks
        policy = baker.make("automation.Policy")
        checks = self.create_policy_checks(policy)
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)

        # test copy tasks and checks to another policy
        data = {
            "name": "Test Copy Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False,
            "copyId": policy.pk,
        }

        resp = self.client.post(f"/automation/policies/", data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(policy.autotasks.count(), 3)
        self.assertEqual(policy.policychecks.count(), 7)

        self.check_not_authenticated("post", url)

    @patch("automation.tasks.generate_agent_checks_from_policies_task.delay")
    def test_update_policy(self, mock_checks_task):
        # returns 404 for invalid policy pk
        resp = self.client.put("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy", active=True, enforced=False)
        url = f"/automation/policies/{policy.pk}/"

        data = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": True,
            "enforced": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # only called if active or enforced are updated
        mock_checks_task.assert_not_called()

        data = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": False,
            "enforced": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_task.assert_called_with(
            policypk=policy.pk, clear=True, create_tasks=True
        )

        self.check_not_authenticated("put", url)

    @patch("automation.tasks.generate_agent_checks_from_policies_task.delay")
    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    def test_delete_policy(self, mock_tasks_task, mock_checks_task):
        # returns 404 for invalid policy pk
        resp = self.client.delete("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")
        url = f"/automation/policies/{policy.pk}/"

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        mock_checks_task.assert_called_with(policypk=policy.pk, clear=True)
        mock_tasks_task.assert_called_with(policypk=policy.pk, clear=True)

        self.check_not_authenticated("delete", url)

    def test_get_all_policy_tasks(self):
        # returns 404 for invalid policy pk
        resp = self.client.get("/automation/500/policyautomatedtasks/", format="json")
        self.assertEqual(resp.status_code, 404)

        # create policy with tasks
        policy = baker.make("automation.Policy")
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
        url = f"/automation/{policy.pk}/policyautomatedtasks/"

        resp = self.client.get(url, format="json")
        serializer = AutoTaskPolicySerializer(policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.assertEqual(len(resp.data), 3)

        self.check_not_authenticated("get", url)

    def test_get_all_policy_checks(self):

        # setup data
        policy = baker.make("automation.Policy")
        checks = self.create_policy_checks(policy)

        url = f"/automation/{policy.pk}/policychecks/"

        resp = self.client.get(url, format="json")
        serializer = PolicyCheckSerializer(checks, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.assertEqual(len(resp.data), 7)

        self.check_not_authenticated("get", url)

    def test_get_policy_check_status(self):
        # set data
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        policy_diskcheck = baker.make_recipe("checks.diskspace_check", policy=policy)
        managed_check = baker.make_recipe(
            "checks.diskspace_check",
            agent=agent,
            managed_by_policy=True,
            parent_check=policy_diskcheck.pk,
        )
        url = f"/automation/policycheckstatus/{policy_diskcheck.pk}/check/"

        resp = self.client.patch(url, format="json")
        serializer = PolicyCheckStatusSerializer([managed_check], many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("patch", url)

    def test_policy_overview(self):
        url = "/automation/policies/overview/"

        policies = baker.make(
            "automation.Policy", active=cycle([True, False]), _quantity=5
        )
        clients = baker.make(
            "clients.Client",
            server_policy=cycle(policies),
            workstation_policy=cycle(policies),
            _quantity=5,
        )
        sites = baker.make(
            "clients.Site",
            client=cycle(clients),
            server_policy=cycle(policies),
            workstation_policy=cycle(policies),
            _quantity=4,
        )

        sites = baker.make("clients.Site", client=cycle(clients), _quantity=3)
        resp = self.client.get(url, format="json")
        serializer = PolicyOverviewSerializer(clients, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_get_related(self):
        policy = baker.make("automation.Policy")
        url = f"/automation/policies/{policy.pk}/related/"

        resp = self.client.get(url, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data["server_clients"], list)
        self.assertIsInstance(resp.data["workstation_clients"], list)
        self.assertIsInstance(resp.data["server_sites"], list)
        self.assertIsInstance(resp.data["workstation_sites"], list)
        self.assertIsInstance(resp.data["agents"], list)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.generate_checks_from_policies")
    @patch("automation.tasks.generate_agent_checks_by_location_task.delay")
    def test_update_policy_add(
        self,
        mock_checks_location_task,
        mock_checks_task,
    ):
        url = f"/automation/related/"

        # data setup
        policy = baker.make("automation.Policy")
        client = baker.make("clients.Client", client="Test Client")
        site = baker.make("clients.Site", client=client, site="Test Site")
        agent = baker.make_recipe("agents.agent", client=client.client, site=site.site)

        # test add client to policy data
        client_server_payload = {
            "type": "client",
            "pk": client.pk,
            "server_policy": policy.pk,
        }
        client_workstation_payload = {
            "type": "client",
            "pk": client.pk,
            "workstation_policy": policy.pk,
        }

        # test add site to policy data
        site_server_payload = {
            "type": "site",
            "pk": site.pk,
            "server_policy": policy.pk,
        }
        site_workstation_payload = {
            "type": "site",
            "pk": site.pk,
            "workstation_policy": policy.pk,
        }

        # test add agent to policy data
        agent_payload = {"type": "agent", "pk": agent.pk, "policy": policy.pk}

        # test client server policy add
        resp = self.client.post(url, client_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": client.client},
            mon_type="server",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test client workstation policy add
        resp = self.client.post(url, client_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": client.client},
            mon_type="workstation",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test site add server policy
        resp = self.client.post(url, site_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site},
            mon_type="server",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test site add workstation policy
        resp = self.client.post(url, site_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site},
            mon_type="workstation",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test agent add
        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_task.assert_called_with(clear=True)
        mock_checks_task.reset_mock()

        # Adding the same relations shouldn't trigger mocks
        resp = self.client.post(url, client_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, client_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_location_task.assert_not_called()

        resp = self.client.post(url, site_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, site_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_location_task.assert_not_called()

        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_task.assert_not_called()

        # test remove client from policy data
        client_server_payload = {"type": "client", "pk": client.pk, "server_policy": 0}
        client_workstation_payload = {
            "type": "client",
            "pk": client.pk,
            "workstation_policy": 0,
        }

        # test remove site from policy data
        site_server_payload = {"type": "site", "pk": site.pk, "server_policy": 0}
        site_workstation_payload = {
            "type": "site",
            "pk": site.pk,
            "workstation_policy": 0,
        }

        # test remove agent from policy
        agent_payload = {"type": "agent", "pk": agent.pk, "policy": 0}

        # test client server policy remove
        resp = self.client.post(url, client_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": client.client},
            mon_type="server",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test client workstation policy remove
        resp = self.client.post(url, client_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": client.client},
            mon_type="workstation",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test site remove server policy
        resp = self.client.post(url, site_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site},
            mon_type="server",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test site remove workstation policy
        resp = self.client.post(url, site_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site},
            mon_type="workstation",
            clear=True,
            create_tasks=True,
        )
        mock_checks_location_task.reset_mock()

        # test agent remove
        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        # called because the relation changed
        mock_checks_task.assert_called_with(clear=True)
        mock_checks_task.reset_mock()

        # adding the same relations shouldn't trigger mocks
        resp = self.client.post(url, client_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(url, client_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_location_task.assert_not_called()

        resp = self.client.post(url, site_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(url, site_workstation_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_location_task.assert_not_called()

        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_task.assert_not_called()

        self.check_not_authenticated("post", url)

    def test_relation_by_type(self):
        url = f"/automation/related/"

        # data setup
        policy = baker.make("automation.Policy")
        client = baker.make("clients.Client", client="Test Client")
        site = baker.make("clients.Site", client=client, site="Test Site")
        agent = baker.make_recipe("agents.agent", client=client.client, site=site.site)

        client_payload = {"type": "client", "pk": client.pk}

        # test add site to policy
        site_payload = {"type": "site", "pk": site.pk}

        # test add agent to policy
        agent_payload = {"type": "agent", "pk": agent.pk}

        # test client relation get
        serializer = RelatedClientPolicySerializer(client)
        resp = self.client.patch(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # test site relation get
        serializer = RelatedSitePolicySerializer(site)
        resp = self.client.patch(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # test agent relation get
        serializer = RelatedAgentPolicySerializer(agent)
        resp = self.client.patch(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        invalid_payload = {"type": "bad_type", "pk": 5}

        resp = self.client.patch(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("patch", url)

    @patch("automation.tasks.run_win_policy_autotask_task.delay")
    def test_run_win_task(self, mock_task):

        # create managed policy tasks
        tasks = baker.make(
            "autotasks.AutomatedTask",
            managed_by_policy=True,
            parent_task=1,
            _quantity=6,
        )
        url = "/automation/runwintask/1/"
        resp = self.client.put(url, format="json")
        self.assertEqual(resp.status_code, 200)

        mock_task.assert_called_once_with([task.pk for task in tasks])

        self.check_not_authenticated("put", url)

    def test_create_new_patch_policy(self):
        url = "/automation/winupdatepolicy/"

        # test policy doesn't exist
        data = {"policy": 500}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")

        data = {
            "policy": policy.pk,
            "critical": "approve",
            "important": "approve",
            "moderate": "ignore",
            "low": "ignore",
            "other": "approve",
            "run_time_hour": 3,
            "run_time_frequency": "daily",
            "run_time_days": [0, 3, 5],
            "run_time_day": "15",
            "reboot_after_install": "always",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_update_patch_policy(self):

        # test policy doesn't exist
        resp = self.client.put("/automation/winupdatepolicy/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")
        patch_policy = baker.make("winupdate.WinUpdatePolicy", policy=policy)
        url = f"/automation/winupdatepolicy/{patch_policy.pk}/"

        data = {
            "id": patch_policy.pk,
            "policy": policy.pk,
            "critical": "approve",
            "important": "approve",
            "moderate": "ignore",
            "low": "ignore",
            "other": "approve",
            "run_time_days": [4, 5, 6],
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("put", url)

    def test_reset_patch_policy(self):
        url = "/automation/winupdatepolicy/reset/"

        inherit_fields = {
            "critical": "inherit",
            "important": "inherit",
            "moderate": "inherit",
            "low": "inherit",
            "other": "inherit",
            "run_time_frequency": "inherit",
            "reboot_after_install": "inherit",
            "reprocess_failed_inherit": True,
        }

        # create agents in sites
        clients = baker.make("clients.Client", client=seq("Client"), _quantity=3)
        sites = baker.make(
            "clients.Site", client=cycle(clients), site=seq("Site"), _quantity=6
        )

        agents = baker.make_recipe(
            "agents.agent",
            client=cycle([x.client for x in clients]),
            site=cycle([x.site for x in sites]),
            _quantity=6,
        )

        # create patch policies
        patch_policies = baker.make_recipe(
            "winupdate.winupdate_approve", agent=cycle(agents), _quantity=6
        )

        # test reset agents in site
        data = {"client": clients[0].client, "site": "Site0"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(client=clients[0].client, site="Site0")

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset agents in client
        data = {"client": clients[1].client}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(client=clients[1].client)

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset all agents
        data = {}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.all()
        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        self.check_not_authenticated("patch", url)

    def test_delete_patch_policy(self):
        # test patch policy doesn't exist
        resp = self.client.delete("/automation/winupdatepolicy/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        winupdate_policy = baker.make_recipe(
            "winupdate.winupdate_policy", policy__name="Test Policy"
        )
        url = f"/automation/winupdatepolicy/{winupdate_policy.pk}/"

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            WinUpdatePolicy.objects.filter(pk=winupdate_policy.pk).exists()
        )

        self.check_not_authenticated("delete", url)


class TestPolicyTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_policy_related(self):

        # Get Site and Client from an agent in list
        clients = baker.make("clients.Client", client=seq("Client"), _quantity=5)
        sites = baker.make(
            "clients.Site", client=cycle(clients), site=seq("Site"), _quantity=25
        )
        server_agents = baker.make_recipe(
            "agents.server_agent",
            client=cycle([x.client for x in clients]),
            site=seq("Site"),
            _quantity=25,
        )
        workstation_agents = baker.make_recipe(
            "agents.workstation_agent",
            client=cycle([x.client for x in clients]),
            site=seq("Site"),
            _quantity=25,
        )

        server_client = clients[3]
        server_site = server_client.sites.all()[3]
        workstation_client = clients[1]
        workstation_site = server_client.sites.all()[2]
        server_agent = baker.make_recipe(
            "agents.server_agent", client=server_client.client, site=server_site.site
        )
        workstation_agent = baker.make_recipe(
            "agents.workstation_agent",
            client=workstation_client.client,
            site=workstation_site.site,
        )
        policy = baker.make("automation.Policy", active=True)

        # Add Client to Policy
        policy.server_clients.add(server_client)
        policy.workstation_clients.add(workstation_client)

        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEquals(len(resp.data["server_clients"]), 1)
        self.assertEquals(len(resp.data["server_sites"]), 5)
        self.assertEquals(len(resp.data["workstation_clients"]), 1)
        self.assertEquals(len(resp.data["workstation_sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 12)

        # Add Site to Policy and the agents and sites length shouldn't change
        policy.server_sites.add(server_site)
        policy.workstation_sites.add(workstation_site)
        self.assertEquals(len(resp.data["server_sites"]), 5)
        self.assertEquals(len(resp.data["workstation_sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 12)

        # Add Agent to Policy and the agents length shouldn't change
        policy.agents.add(server_agent)
        policy.agents.add(workstation_agent)
        self.assertEquals(len(resp.data["agents"]), 12)
