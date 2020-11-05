from unittest.mock import patch
from tacticalrmm.test import TacticalTestCase
from model_bakery import baker, seq
from itertools import cycle
from agents.models import Agent
from winupdate.models import WinUpdatePolicy

from .serializers import (
    PolicyTableSerializer,
    PolicySerializer,
    PolicyTaskStatusSerializer,
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
        self.create_checks(policy=policy)
        baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)

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
        baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
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
        checks = self.create_checks(policy=policy)

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
        from clients.models import Client

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
        baker.make(
            "clients.Site",
            client=cycle(clients),
            server_policy=cycle(policies),
            workstation_policy=cycle(policies),
            _quantity=4,
        )

        baker.make("clients.Site", client=cycle(clients), _quantity=3)
        resp = self.client.get(url, format="json")
        clients = Client.objects.all()
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
        client = baker.make("clients.Client")
        site = baker.make("clients.Site", client=client)
        agent = baker.make_recipe("agents.agent", site=site)

        # test add client to policy data
        client_server_payload = {
            "type": "client",
            "pk": agent.client.pk,
            "server_policy": policy.pk,
        }
        client_workstation_payload = {
            "type": "client",
            "pk": agent.client.pk,
            "workstation_policy": policy.pk,
        }

        # test add site to policy data
        site_server_payload = {
            "type": "site",
            "pk": agent.site.pk,
            "server_policy": policy.pk,
        }
        site_workstation_payload = {
            "type": "site",
            "pk": agent.site.pk,
            "workstation_policy": policy.pk,
        }

        # test add agent to policy data
        agent_payload = {"type": "agent", "pk": agent.pk, "policy": policy.pk}

        # test client server policy add
        resp = self.client.post(url, client_server_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"site__client_id": client.id},
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
            location={"site__client_id": client.id},
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
            location={"site_id": site.id},
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
            location={"site_id": site.id},
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
            location={"site__client_id": client.id},
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
            location={"site__client_id": client.id},
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
            location={"site_id": site.id},
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
            location={"site_id": site.id},
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

    def test_get_relation_by_type(self):
        url = f"/automation/related/"

        # data setup
        policy = baker.make("automation.Policy")
        client = baker.make("clients.Client", workstation_policy=policy)
        site = baker.make("clients.Site", server_policy=policy)
        agent = baker.make_recipe("agents.agent", site=site, policy=policy)

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

    def test_get_policy_task_status(self):

        # policy with a task
        policy = baker.make("automation.Policy")
        task = baker.make("autotasks.AutomatedTask", policy=policy)

        # create policy managed tasks
        policy_tasks = baker.make(
            "autotasks.AutomatedTask", parent_task=task.id, _quantity=5
        )

        url = f"/automation/policyautomatedtaskstatus/{task.id}/task/"

        serializer = PolicyTaskStatusSerializer(policy_tasks, many=True)
        resp = self.client.patch(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.assertEqual(len(resp.data), 5)

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

        clients = baker.make("clients.Client", _quantity=6)
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=10)
        agents = baker.make_recipe(
            "agents.agent",
            site=cycle(sites),
            _quantity=6,
        )

        # create patch policies
        baker.make_recipe(
            "winupdate.winupdate_approve", agent=cycle(agents), _quantity=6
        )

        # test reset agents in site
        data = {"site": sites[0].id}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site=sites[0])

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset agents in client
        data = {"client": clients[1].id}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site__client=clients[1])

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
        clients = baker.make("clients.Client", _quantity=5)
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=25)
        server_agents = baker.make_recipe(
            "agents.server_agent",
            site=cycle(sites),
            _quantity=25,
        )
        workstation_agents = baker.make_recipe(
            "agents.workstation_agent",
            site=cycle(sites),
            _quantity=25,
        )

        policy = baker.make("automation.Policy", active=True)

        # Add Client to Policy
        policy.server_clients.add(server_agents[13].client)
        policy.workstation_clients.add(workstation_agents[15].client)

        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEquals(len(resp.data["server_clients"]), 1)
        self.assertEquals(len(resp.data["server_sites"]), 5)
        self.assertEquals(len(resp.data["workstation_clients"]), 1)
        self.assertEquals(len(resp.data["workstation_sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 10)

        # Add Site to Policy and the agents and sites length shouldn't change
        policy.server_sites.add(server_agents[13].site)
        policy.workstation_sites.add(workstation_agents[15].site)
        self.assertEquals(len(resp.data["server_sites"]), 5)
        self.assertEquals(len(resp.data["workstation_sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 10)

        # Add Agent to Policy and the agents length shouldn't change
        policy.agents.add(server_agents[13])
        policy.agents.add(workstation_agents[15])
        self.assertEquals(len(resp.data["agents"]), 10)

    def test_generating_agent_policy_checks(self):
        from .tasks import generate_agent_checks_from_policies_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        checks = self.create_checks(policy=policy)
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site, policy=policy)

        # test policy assigned to agent
        generate_agent_checks_from_policies_task(policy.id, clear=True)

        # make sure all checks were created. should be 7
        agent_checks = Agent.objects.get(pk=agent.id).agentchecks.all()
        self.assertEquals(len(agent_checks), 7)

        # make sure checks were copied correctly
        for check in agent_checks:

            self.assertTrue(check.managed_by_policy)
            if check.check_type == "diskspace":
                self.assertEqual(check.parent_check, checks[0].id)
                self.assertEqual(check.disk, checks[0].disk)
                self.assertEqual(check.threshold, checks[0].threshold)
            elif check.check_type == "ping":
                self.assertEqual(check.parent_check, checks[1].id)
                self.assertEqual(check.ip, checks[1].ip)
            elif check.check_type == "cpuload":
                self.assertEqual(check.parent_check, checks[2].id)
                self.assertEqual(check.threshold, checks[2].threshold)
            elif check.check_type == "memory":
                self.assertEqual(check.parent_check, checks[3].id)
                self.assertEqual(check.threshold, checks[3].threshold)
            elif check.check_type == "winsvc":
                self.assertEqual(check.parent_check, checks[4].id)
                self.assertEqual(check.svc_name, checks[4].svc_name)
                self.assertEqual(check.svc_display_name, checks[4].svc_display_name)
                self.assertEqual(check.svc_policy_mode, checks[4].svc_policy_mode)
            elif check.check_type == "script":
                self.assertEqual(check.parent_check, checks[5].id)
                self.assertEqual(check.script, checks[5].script)
            elif check.check_type == "eventlog":
                self.assertEqual(check.parent_check, checks[6].id)
                self.assertEqual(check.event_id, checks[6].event_id)
                self.assertEqual(check.event_type, checks[6].event_type)

    def test_generating_agent_policy_checks_with_enforced(self):
        from .tasks import generate_agent_checks_from_policies_task

        # setup data
        policy = baker.make("automation.Policy", active=True, enforced=True)
        script = baker.make_recipe("scripts.script")
        self.create_checks(policy=policy, script=script)
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site, policy=policy)
        self.create_checks(agent=agent, script=script)

        generate_agent_checks_from_policies_task(policy.id, create_tasks=True)

        # make sure each agent check says overriden_by_policy
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 14)
        self.assertEqual(
            Agent.objects.get(pk=agent.id)
            .agentchecks.filter(overriden_by_policy=True)
            .count(),
            7,
        )

    def test_generating_agent_policy_checks_by_location(self):
        from .tasks import generate_agent_checks_by_location_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)
        clients = baker.make(
            "clients.Client",
            _quantity=2,
            server_policy=policy,
            workstation_policy=policy,
        )
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=4)
        server_agent = baker.make_recipe("agents.server_agent", site=sites[0])
        workstation_agent = baker.make_recipe("agents.workstation_agent", site=sites[2])
        agent1 = baker.make_recipe("agents.server_agent", site=sites[1])
        agent2 = baker.make_recipe("agents.workstation_agent", site=sites[3])

        generate_agent_checks_by_location_task(
            {"site_id": sites[0].id},
            "server",
            clear=True,
            create_tasks=True,
        )

        # server_agent should have policy checks and the other agents should not
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 7)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )
        self.assertEqual(Agent.objects.get(pk=agent1.id).agentchecks.count(), 0)

        generate_agent_checks_by_location_task(
            {"site__client_id": clients[0].id},
            "workstation",
            clear=True,
            create_tasks=True,
        )
        # workstation_agent should now have policy checks and the other agents should not
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 7
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 7)
        self.assertEqual(Agent.objects.get(pk=agent1.id).agentchecks.count(), 0)
        self.assertEqual(Agent.objects.get(pk=agent2.id).agentchecks.count(), 0)

    def test_generating_policy_checks_for_all_agents(self):
        from .tasks import generate_all_agent_checks_task
        from core.models import CoreSettings

        # setup data
        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)

        site = baker.make("clients.Site")
        server_agents = baker.make_recipe("agents.server_agent", site=site, _quantity=3)
        workstation_agents = baker.make_recipe(
            "agents.workstation_agent", site=site, _quantity=4
        )
        core = CoreSettings.objects.first()
        core.server_policy = policy
        core.workstation_policy = policy
        core.save()

        generate_all_agent_checks_task("server", clear=True, create_tasks=True)

        # all servers should have 7 checks
        for agent in server_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        for agent in workstation_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 0)

        generate_all_agent_checks_task("workstation", clear=True, create_tasks=True)

        # all agents should have 7 checks now
        for agent in server_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        for agent in workstation_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

    def test_delete_policy_check(self):
        from .tasks import delete_policy_check_task
        from .models import Policy

        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.server_agent", site=site, policy=policy)
        agent.generate_checks_from_policies()

        # make sure agent has 7 checks
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        # pick a policy check and delete it from the agent
        policy_check_id = Policy.objects.get(pk=policy.id).policychecks.first().id

        delete_policy_check_task(policy_check_id)

        # make sure policy check doesn't exist on agent
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 6)
        self.assertFalse(
            Agent.objects.get(pk=agent.id)
            .agentchecks.filter(parent_check=policy_check_id)
            .exists()
        )

    def update_policy_check_fields(self):
        from .tasks import update_policy_check_fields_task
        from .models import Policy

        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)
        agent = baker.make_recipe("agents.server_agent", policy=policy)
        agent.generate_checks_from_policies()

        # make sure agent has 7 checks
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        # pick a policy check and update it with new values
        ping_check = (
            Policy.objects.get(pk=policy.id)
            .policychecks.filter(check_type="ping")
            .first()
        )
        ping_check.ip = "12.12.12.12"
        ping_check.save()

        update_policy_check_fields_task(ping_check.id)

        # make sure policy check was updated on the agent
        self.assertEquals(
            Agent.objects.get(pk=agent.id)
            .agentchecks.filter(parent_check=ping_check.id)
            .ip,
            "12.12.12.12",
        )

    def test_generate_agent_tasks(self):
        from .tasks import generate_agent_tasks_from_policies_task

        # create test data
        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make(
            "autotasks.AutomatedTask", policy=policy, name=seq("Task"), _quantity=3
        )
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.server_agent", site=site, policy=policy)

        generate_agent_tasks_from_policies_task(policy.id, clear=True)

        agent_tasks = Agent.objects.get(pk=agent.id).autotasks.all()

        # make sure there are 3 agent tasks
        self.assertEqual(len(agent_tasks), 3)

        for task in agent_tasks:
            self.assertTrue(task.managed_by_policy)
            if task.name == "Task1":
                self.assertEqual(task.parent_task, tasks[0].id)
                self.assertEqual(task.name, tasks[0].name)
            if task.name == "Task2":
                self.assertEqual(task.parent_task, tasks[1].id)
                self.assertEqual(task.name, tasks[1].name)
            if task.name == "Task3":
                self.assertEqual(task.parent_task, tasks[2].id)
                self.assertEqual(task.name, tasks[2].name)

    def test_generate_agent_tasks_by_location(self):
        from .tasks import generate_agent_tasks_by_location_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        baker.make(
            "autotasks.AutomatedTask", policy=policy, name=seq("Task"), _quantity=3
        )
        clients = baker.make(
            "clients.Client",
            _quantity=2,
            server_policy=policy,
            workstation_policy=policy,
        )
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=4)
        server_agent = baker.make_recipe("agents.server_agent", site=sites[0])
        workstation_agent = baker.make_recipe("agents.workstation_agent", site=sites[2])
        agent1 = baker.make_recipe("agents.agent", site=sites[1])
        agent2 = baker.make_recipe("agents.agent", site=sites[3])

        generate_agent_tasks_by_location_task(
            {"site_id": sites[0].id}, "server", clear=True
        )

        # all servers in site1 and site2 should have 3 tasks
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).autotasks.count(), 0
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).autotasks.count(), 3)
        self.assertEqual(Agent.objects.get(pk=agent1.id).autotasks.count(), 0)
        self.assertEqual(Agent.objects.get(pk=agent2.id).autotasks.count(), 0)

        generate_agent_tasks_by_location_task(
            {"site__client_id": clients[0].id}, "workstation", clear=True
        )

        # all workstations in Default1 should have 3 tasks
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).autotasks.count(), 3
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).autotasks.count(), 3)
        self.assertEqual(Agent.objects.get(pk=agent1.id).autotasks.count(), 0)
        self.assertEqual(Agent.objects.get(pk=agent2.id).autotasks.count(), 0)

    @patch("autotasks.tasks.delete_win_task_schedule.delay")
    def test_delete_policy_tasks(self, delete_win_task_schedule):
        from .tasks import delete_policy_autotask_task

        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.server_agent", site=site, policy=policy)
        agent.generate_tasks_from_policies()

        delete_policy_autotask_task(tasks[0].id)

        delete_win_task_schedule.assert_called_with(agent.autotasks.first().id)

    @patch("autotasks.tasks.run_win_task.delay")
    def test_run_policy_task(self, run_win_task):
        from .tasks import run_win_policy_autotask_task

        tasks = baker.make("autotasks.AutomatedTask", _quantity=3)

        run_win_policy_autotask_task([task.id for task in tasks])

        run_win_task.side_effect = [task.id for task in tasks]
        self.assertEqual(run_win_task.call_count, 3)
        for task in tasks:
            run_win_task.assert_any_call(task.id)

    def test_update_policy_tasks(self):
        from .tasks import update_policy_task_fields_task
        from autotasks.models import AutomatedTask

        # setup data
        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make(
            "autotasks.AutomatedTask", enabled=True, policy=policy, _quantity=3
        )
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.server_agent", site=site, policy=policy)
        agent.generate_tasks_from_policies()

        tasks[0].enabled = False
        tasks[0].save()

        update_policy_task_fields_task(tasks[0].id, enabled=False)

        self.assertFalse(AutomatedTask.objects.get(parent_task=tasks[0].id).enabled)
