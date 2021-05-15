from itertools import cycle
from unittest.mock import patch

from agents.models import Agent
from core.models import CoreSettings
from model_bakery import baker, seq
from tacticalrmm.test import TacticalTestCase
from winupdate.models import WinUpdatePolicy

from .serializers import (
    AutoTasksFieldSerializer,
    PolicyCheckSerializer,
    PolicyCheckStatusSerializer,
    PolicyOverviewSerializer,
    PolicySerializer,
    PolicyTableSerializer,
    PolicyTaskStatusSerializer,
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
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_policy(self):
        # returns 404 for invalid policy pk
        resp = self.client.get("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")
        url = f"/automation/policies/{policy.pk}/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = PolicySerializer(policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    def test_add_policy(self, create_task):
        from automation.models import Policy

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
        checks = self.create_checks(policy=policy)
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)

        # assign a task to a check
        tasks[0].assigned_check = checks[0]  # type: ignore
        tasks[0].save()  # type: ignore

        # test copy tasks and checks to another policy
        data = {
            "name": "Test Copy Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False,
            "copyId": policy.pk,  # type: ignore
        }

        resp = self.client.post(f"/automation/policies/", data, format="json")
        self.assertEqual(resp.status_code, 200)

        copied_policy = Policy.objects.get(name=data["name"])

        self.assertEqual(copied_policy.autotasks.count(), 3)  # type: ignore
        self.assertEqual(copied_policy.policychecks.count(), 7)  # type: ignore

        # make sure correct task was assign to the check
        self.assertEqual(copied_policy.autotasks.get(name=tasks[0].name).assigned_check.check_type, checks[0].check_type)  # type: ignore

        create_task.assert_not_called()

        self.check_not_authenticated("post", url)

    @patch("automation.tasks.generate_agent_checks_task.delay")
    def test_update_policy(self, generate_agent_checks_task):
        # returns 404 for invalid policy pk
        resp = self.client.put("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy", active=True, enforced=False)
        url = f"/automation/policies/{policy.pk}/"  # type: ignore

        data = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": True,
            "enforced": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # only called if active, enforced, or excluded objects are updated
        generate_agent_checks_task.assert_not_called()

        data = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": False,
            "enforced": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        generate_agent_checks_task.assert_called_with(
            policy=policy.pk, create_tasks=True  # type: ignore
        )
        generate_agent_checks_task.reset_mock()

        # make sure policies are re-evaluated when excluded changes
        agents = baker.make_recipe("agents.agent", _quantity=2)
        clients = baker.make("clients.Client", _quantity=2)
        sites = baker.make("clients.Site", _quantity=2)
        data = {
            "excluded_agents": [agent.pk for agent in agents],  # type: ignore
            "excluded_sites": [site.pk for site in sites],  # type: ignore
            "excluded_clients": [client.pk for client in clients],  # type: ignore
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        generate_agent_checks_task.assert_called_with(
            policy=policy.pk, create_tasks=True  # type: ignore
        )

        self.check_not_authenticated("put", url)

    @patch("automation.tasks.generate_agent_checks_task.delay")
    def test_delete_policy(self, generate_agent_checks_task):
        # returns 404 for invalid policy pk
        resp = self.client.delete("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # setup data
        policy = baker.make("automation.Policy")
        site = baker.make("clients.Site")
        agents = baker.make_recipe(
            "agents.agent", site=site, policy=policy, _quantity=3
        )
        url = f"/automation/policies/{policy.pk}/"  # type: ignore

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        generate_agent_checks_task.assert_called_with(
            agents=[agent.pk for agent in agents], create_tasks=True
        )

        self.check_not_authenticated("delete", url)

    def test_get_all_policy_tasks(self):
        # create policy with tasks
        policy = baker.make("automation.Policy")
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
        url = f"/automation/{policy.pk}/policyautomatedtasks/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = AutoTasksFieldSerializer(tasks, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.assertEqual(len(resp.data), 3)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_all_policy_checks(self):

        # setup data
        policy = baker.make("automation.Policy")
        checks = self.create_checks(policy=policy)

        url = f"/automation/{policy.pk}/policychecks/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = PolicyCheckSerializer(checks, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.assertEqual(len(resp.data), 7)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_policy_check_status(self):
        # setup data
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site)
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
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.check_not_authenticated("patch", url)

    def test_policy_overview(self):
        from clients.models import Client

        url = "/automation/policies/overview/"

        policies = baker.make(
            "automation.Policy", active=cycle([True, False]), _quantity=5
        )
        clients = baker.make(
            "clients.Client",
            server_policy=cycle(policies),  # type: ignore
            workstation_policy=cycle(policies),  # type: ignore
            _quantity=5,
        )
        baker.make(
            "clients.Site",
            client=cycle(clients),  # type: ignore
            server_policy=cycle(policies),  # type: ignore
            workstation_policy=cycle(policies),  # type: ignore
            _quantity=4,
        )

        baker.make("clients.Site", client=cycle(clients), _quantity=3)  # type: ignore
        resp = self.client.get(url, format="json")
        clients = Client.objects.all()
        serializer = PolicyOverviewSerializer(clients, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_related(self):
        policy = baker.make("automation.Policy")
        url = f"/automation/policies/{policy.pk}/related/"  # type: ignore

        resp = self.client.get(url, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data["server_clients"], list)  # type: ignore
        self.assertIsInstance(resp.data["workstation_clients"], list)  # type: ignore
        self.assertIsInstance(resp.data["server_sites"], list)  # type: ignore
        self.assertIsInstance(resp.data["workstation_sites"], list)  # type: ignore
        self.assertIsInstance(resp.data["agents"], list)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_get_policy_task_status(self):

        # policy with a task
        policy = baker.make("automation.Policy")
        task = baker.make("autotasks.AutomatedTask", policy=policy)

        # create policy managed tasks
        policy_tasks = baker.make(
            "autotasks.AutomatedTask", parent_task=task.id, _quantity=5  # type: ignore
        )

        url = f"/automation/policyautomatedtaskstatus/{task.id}/task/"  # type: ignore

        serializer = PolicyTaskStatusSerializer(policy_tasks, many=True)
        resp = self.client.patch(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.assertEqual(len(resp.data), 5)  # type: ignore

        self.check_not_authenticated("patch", url)

    @patch("automation.tasks.run_win_policy_autotasks_task.delay")
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

        mock_task.assert_called()  # type: ignore

        self.check_not_authenticated("put", url)

    def test_create_new_patch_policy(self):
        url = "/automation/winupdatepolicy/"

        # test policy doesn't exist
        data = {"policy": 500}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")

        data = {
            "policy": policy.pk,  # type: ignore
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
        url = f"/automation/winupdatepolicy/{patch_policy.pk}/"  # type: ignore

        data = {
            "id": patch_policy.pk,  # type: ignore
            "policy": policy.pk,  # type: ignore
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
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=10)  # type: ignore
        agents = baker.make_recipe(
            "agents.agent",
            site=cycle(sites),  # type: ignore
            _quantity=6,
        )

        # create patch policies
        baker.make_recipe(
            "winupdate.winupdate_approve", agent=cycle(agents), _quantity=6
        )

        # test reset agents in site
        data = {"site": sites[0].id}  # type: ignore

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site=sites[0])  # type: ignore

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset agents in client
        data = {"client": clients[1].id}  # type: ignore

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site__client=clients[1])  # type: ignore

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

    @patch("automation.tasks.generate_agent_checks_task.delay")
    def test_sync_policy(self, generate_checks):
        url = "/automation/sync/"

        # test invalid data
        data = {"invalid": 7}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        policy = baker.make("automation.Policy", active=True)
        data = {"policy": policy.pk}  # type: ignore

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        generate_checks.assert_called_with(policy=policy.pk, create_tasks=True)  # type: ignore

        self.check_not_authenticated("post", url)


class TestPolicyTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_policy_related(self):

        # Get Site and Client from an agent in list
        clients = baker.make("clients.Client", _quantity=5)
        sites = baker.make("clients.Site", client=cycle(clients), _quantity=25)  # type: ignore
        server_agents = baker.make_recipe(
            "agents.server_agent",
            site=cycle(sites),  # type: ignore
            _quantity=25,
        )
        workstation_agents = baker.make_recipe(
            "agents.workstation_agent",
            site=cycle(sites),  # type: ignore
            _quantity=25,
        )

        policy = baker.make("automation.Policy", active=True)

        # Add Client to Policy
        policy.server_clients.add(server_agents[13].client)  # type: ignore
        policy.workstation_clients.add(workstation_agents[15].client)  # type: ignore

        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"  # type: ignore
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEquals(len(resp.data["server_clients"]), 1)  # type: ignore
        self.assertEquals(len(resp.data["server_sites"]), 5)  # type: ignore
        self.assertEquals(len(resp.data["workstation_clients"]), 1)  # type: ignore
        self.assertEquals(len(resp.data["workstation_sites"]), 5)  # type: ignore
        self.assertEquals(len(resp.data["agents"]), 10)  # type: ignore

        # Add Site to Policy and the agents and sites length shouldn't change
        policy.server_sites.add(server_agents[13].site)  # type: ignore
        policy.workstation_sites.add(workstation_agents[15].site)  # type: ignore
        self.assertEquals(len(resp.data["server_sites"]), 5)  # type: ignore
        self.assertEquals(len(resp.data["workstation_sites"]), 5)  # type: ignore
        self.assertEquals(len(resp.data["agents"]), 10)  # type: ignore

        # Add Agent to Policy and the agents length shouldn't change
        policy.agents.add(server_agents[13])  # type: ignore
        policy.agents.add(workstation_agents[15])  # type: ignore
        self.assertEquals(len(resp.data["agents"]), 10)  # type: ignore

    def test_generating_agent_policy_checks(self):
        from .tasks import generate_agent_checks_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        checks = self.create_checks(policy=policy)
        agent = baker.make_recipe("agents.agent", policy=policy)

        # test policy assigned to agent
        generate_agent_checks_task(policy=policy.id)  # type: ignore

        # make sure all checks were created. should be 7
        agent_checks = Agent.objects.get(pk=agent.id).agentchecks.all()
        self.assertEquals(len(agent_checks), 7)

        # make sure checks were copied correctly
        for check in agent_checks:

            self.assertTrue(check.managed_by_policy)
            if check.check_type == "diskspace":
                self.assertEqual(check.parent_check, checks[0].id)
                self.assertEqual(check.disk, checks[0].disk)
                self.assertEqual(check.error_threshold, checks[0].error_threshold)
                self.assertEqual(check.warning_threshold, checks[0].warning_threshold)
            elif check.check_type == "ping":
                self.assertEqual(check.parent_check, checks[1].id)
                self.assertEqual(check.ip, checks[1].ip)
            elif check.check_type == "cpuload":
                self.assertEqual(check.parent_check, checks[2].id)
                self.assertEqual(check.error_threshold, checks[2].error_threshold)
                self.assertEqual(check.warning_threshold, checks[2].warning_threshold)
            elif check.check_type == "memory":
                self.assertEqual(check.parent_check, checks[3].id)
                self.assertEqual(check.error_threshold, checks[3].error_threshold)
                self.assertEqual(check.warning_threshold, checks[3].warning_threshold)
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
        from .tasks import generate_agent_checks_task

        # setup data
        policy = baker.make("automation.Policy", active=True, enforced=True)
        script = baker.make_recipe("scripts.script")
        self.create_checks(policy=policy, script=script)
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site, policy=policy)
        self.create_checks(agent=agent, script=script)

        generate_agent_checks_task(policy=policy.id, create_tasks=True)  # type: ignore

        # make sure each agent check says overriden_by_policy
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 14)
        self.assertEqual(
            Agent.objects.get(pk=agent.id)
            .agentchecks.filter(overriden_by_policy=True)
            .count(),
            7,
        )

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    @patch("automation.tasks.generate_agent_checks_task.delay")
    def test_generating_agent_policy_checks_by_location(
        self, generate_agent_checks_mock, create_task
    ):
        from automation.tasks import generate_agent_checks_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)

        baker.make(
            "autotasks.AutomatedTask", policy=policy, name=seq("Task"), _quantity=3
        )

        server_agent = baker.make_recipe("agents.server_agent")
        workstation_agent = baker.make_recipe("agents.workstation_agent")

        # no checks should be preset on agents
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )

        # set workstation policy on client and policy checks should be there
        workstation_agent.client.workstation_policy = policy
        workstation_agent.client.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            client=workstation_agent.client.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            client=workstation_agent.client.pk,
            create_tasks=True,
        )

        # make sure the checks were added
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 7
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)

        # remove workstation policy from client
        workstation_agent.client.workstation_policy = None
        workstation_agent.client.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            client=workstation_agent.client.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            client=workstation_agent.client.pk,
            create_tasks=True,
        )

        # make sure the checks were removed
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)

        # set server policy on client and policy checks should be there
        server_agent.client.server_policy = policy
        server_agent.client.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            client=server_agent.client.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            client=server_agent.client.pk,
            create_tasks=True,
        )

        # make sure checks were added
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 7)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )

        # remove server policy from client
        server_agent.client.server_policy = None
        server_agent.client.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            client=server_agent.client.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            client=server_agent.client.pk,
            create_tasks=True,
        )

        # make sure checks were removed
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )

        # set workstation policy on site and policy checks should be there
        workstation_agent.site.workstation_policy = policy
        workstation_agent.site.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            site=workstation_agent.site.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            site=workstation_agent.site.pk,
            create_tasks=True,
        )

        # make sure checks were added on workstation
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 7
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)

        # remove workstation policy from site
        workstation_agent.site.workstation_policy = None
        workstation_agent.site.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            site=workstation_agent.site.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            site=workstation_agent.site.pk,
            create_tasks=True,
        )

        # make sure checks were removed
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)

        # set server policy on site and policy checks should be there
        server_agent.site.server_policy = policy
        server_agent.site.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            site=server_agent.site.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            site=server_agent.site.pk,
            create_tasks=True,
        )

        # make sure checks were added
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 7)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )

        # remove server policy from site
        server_agent.site.server_policy = None
        server_agent.site.save()

        # should trigger task in save method on core
        generate_agent_checks_mock.assert_called_with(
            site=server_agent.site.pk,
            create_tasks=True,
        )
        generate_agent_checks_mock.reset_mock()

        generate_agent_checks_task(
            site=server_agent.site.pk,
            create_tasks=True,
        )

        # make sure checks were removed
        self.assertEqual(Agent.objects.get(pk=server_agent.id).agentchecks.count(), 0)
        self.assertEqual(
            Agent.objects.get(pk=workstation_agent.id).agentchecks.count(), 0
        )

    @patch("automation.tasks.generate_agent_checks_task.delay")
    def test_generating_policy_checks_for_all_agents(self, generate_agent_checks_mock):
        from core.models import CoreSettings

        from .tasks import generate_agent_checks_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)

        server_agents = baker.make_recipe("agents.server_agent", _quantity=3)
        workstation_agents = baker.make_recipe("agents.workstation_agent", _quantity=4)
        core = CoreSettings.objects.first()
        core.server_policy = policy
        core.save()

        generate_agent_checks_mock.assert_called_with(all=True, create_tasks=True)
        generate_agent_checks_mock.reset_mock()
        generate_agent_checks_task(all=True, create_tasks=True)

        # all servers should have 7 checks
        for agent in server_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        for agent in workstation_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 0)

        core.server_policy = None
        core.workstation_policy = policy
        core.save()

        generate_agent_checks_mock.assert_any_call(all=True, create_tasks=True)
        generate_agent_checks_mock.reset_mock()
        generate_agent_checks_task(all=True, create_tasks=True)

        # all workstations should have 7 checks
        for agent in server_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 0)

        for agent in workstation_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        core.workstation_policy = None
        core.save()

        generate_agent_checks_mock.assert_called_with(all=True, create_tasks=True)
        generate_agent_checks_mock.reset_mock()
        generate_agent_checks_task(all=True, create_tasks=True)

        # nothing should have the checks
        for agent in server_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 0)

        for agent in workstation_agents:
            self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 0)

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    def update_policy_check_fields(self, create_task):
        from .models import Policy
        from .tasks import update_policy_check_fields_task

        policy = baker.make("automation.Policy", active=True)
        self.create_checks(policy=policy)
        agent = baker.make_recipe("agents.server_agent", policy=policy)

        # make sure agent has 7 checks
        self.assertEqual(Agent.objects.get(pk=agent.id).agentchecks.count(), 7)

        # pick a policy check and update it with new values
        ping_check = (
            Policy.objects.get(pk=policy.id)  # type: ignore
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

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    def test_generate_agent_tasks(self, create_task):
        from .tasks import generate_agent_autotasks_task

        # create test data
        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make(
            "autotasks.AutomatedTask", policy=policy, name=seq("Task"), _quantity=3
        )
        agent = baker.make_recipe("agents.server_agent", policy=policy)

        generate_agent_autotasks_task(policy=policy.id)  # type: ignore

        agent_tasks = Agent.objects.get(pk=agent.id).autotasks.all()

        # make sure there are 3 agent tasks
        self.assertEqual(len(agent_tasks), 3)

        for task in agent_tasks:
            self.assertTrue(task.managed_by_policy)
            if task.name == "Task1":
                self.assertEqual(task.parent_task, tasks[0].id)  # type: ignore
                self.assertEqual(task.name, tasks[0].name)  # type: ignore
            if task.name == "Task2":
                self.assertEqual(task.parent_task, tasks[1].id)  # type: ignore
                self.assertEqual(task.name, tasks[1].name)  # type: ignore
            if task.name == "Task3":
                self.assertEqual(task.parent_task, tasks[2].id)  # type: ignore
                self.assertEqual(task.name, tasks[2].name)  # type: ignore

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    @patch("autotasks.models.AutomatedTask.delete_task_on_agent")
    def test_delete_policy_tasks(self, delete_task_on_agent, create_task):
        from .tasks import delete_policy_autotasks_task

        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
        baker.make_recipe("agents.server_agent", policy=policy)

        delete_policy_autotasks_task(task=tasks[0].id)  # type: ignore

        delete_task_on_agent.assert_called()

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    @patch("autotasks.models.AutomatedTask.run_win_task")
    def test_run_policy_task(self, run_win_task, create_task):
        from .tasks import run_win_policy_autotasks_task

        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=3)
        baker.make_recipe("agents.server_agent", policy=policy)

        run_win_policy_autotasks_task(task=tasks[0].id)  # type: ignore

        run_win_task.assert_called_once()

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    @patch("autotasks.models.AutomatedTask.modify_task_on_agent")
    def test_update_policy_tasks(self, modify_task_on_agent, create_task):
        from .tasks import update_policy_autotasks_fields_task

        # setup data
        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make(
            "autotasks.AutomatedTask",
            enabled=True,
            policy=policy,
            _quantity=3,
        )
        agent = baker.make_recipe("agents.server_agent", policy=policy)

        tasks[0].enabled = False  # type: ignore
        tasks[0].save()  # type: ignore

        update_policy_autotasks_fields_task(task=tasks[0].id)  # type: ignore
        modify_task_on_agent.assert_not_called()

        self.assertFalse(agent.autotasks.get(parent_task=tasks[0].id).enabled)  # type: ignore

        update_policy_autotasks_fields_task(task=tasks[0].id, update_agent=True)  # type: ignore
        modify_task_on_agent.assert_not_called()

        agent.autotasks.update(sync_status="synced")
        update_policy_autotasks_fields_task(task=tasks[0].id, update_agent=True)  # type: ignore
        modify_task_on_agent.assert_called_once()

    @patch("agents.models.Agent.generate_tasks_from_policies")
    @patch("agents.models.Agent.generate_checks_from_policies")
    def test_generate_agent_checks_with_agentpks(self, generate_checks, generate_tasks):
        from automation.tasks import generate_agent_checks_task

        agents = baker.make_recipe("agents.agent", _quantity=5)

        # reset because creating agents triggers it
        generate_checks.reset_mock()
        generate_tasks.reset_mock()

        generate_agent_checks_task(agents=[agent.pk for agent in agents])
        self.assertEquals(generate_checks.call_count, 5)
        generate_tasks.assert_not_called()
        generate_checks.reset_mock()

        generate_agent_checks_task(
            agents=[agent.pk for agent in agents], create_tasks=True
        )
        self.assertEquals(generate_checks.call_count, 5)
        self.assertEquals(generate_checks.call_count, 5)

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    def test_policy_exclusions(self, create_task):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        baker.make_recipe("checks.memory_check", policy=policy)
        task = baker.make("autotasks.AutomatedTask", policy=policy)
        agent = baker.make_recipe(
            "agents.agent", policy=policy, monitoring_type="server"
        )

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 1)  # type: ignore
        self.assertEqual(agent.autotasks.count(), 1)  # type: ignore

        # add agent to policy exclusions
        policy.excluded_agents.set([agent])  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertEqual(policy.related_agents().count(), 0)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 0)  # type: ignore

        # delete agent tasks
        agent.autotasks.all().delete()
        policy.excluded_agents.clear()  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 1)  # type: ignore
        self.assertEqual(agent.autotasks.count(), 1)  # type: ignore

        # add policy exclusions to site
        policy.excluded_sites.set([agent.site])  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertEqual(policy.related_agents().count(), 0)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 0)  # type: ignore

        # delete agent tasks and reset
        agent.autotasks.all().delete()
        policy.excluded_sites.clear()  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 1)  # type: ignore
        self.assertEqual(agent.autotasks.count(), 1)  # type: ignore

        # add policy exclusions to client
        policy.excluded_clients.set([agent.client])  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertEqual(policy.related_agents().count(), 0)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 0)  # type: ignore

        # delete agent tasks and reset
        agent.autotasks.all().delete()
        policy.excluded_clients.clear()  # type: ignore
        agent.policy = None
        agent.save()

        # test on default policy
        core = CoreSettings.objects.first()
        core.server_policy = policy
        core.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(agent.agentchecks.count(), 1)  # type: ignore
        self.assertEqual(agent.autotasks.count(), 1)  # type: ignore

        # add policy exclusions to client
        policy.excluded_clients.set([agent.client])  # type: ignore

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertEqual(policy.related_agents().count(), 0)  # type: ignore
        self.assertEqual(agent.agentchecks.count(), 0)  # type: ignore

    @patch("autotasks.models.AutomatedTask.create_task_on_agent")
    def test_policy_inheritance_blocking(self, create_task):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        baker.make_recipe("checks.memory_check", policy=policy)
        baker.make("autotasks.AutomatedTask", policy=policy)
        agent = baker.make_recipe("agents.agent", monitoring_type="server")

        core = CoreSettings.objects.first()
        core.server_policy = policy
        core.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # should get policies from default policy
        self.assertTrue(agent.autotasks.all())
        self.assertTrue(agent.agentchecks.all())

        # test client blocking inheritance
        agent.site.client.block_policy_inheritance = True
        agent.site.client.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertFalse(agent.autotasks.all())
        self.assertFalse(agent.agentchecks.all())

        agent.site.client.server_policy = policy
        agent.site.client.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # should get policies from client policy
        self.assertTrue(agent.autotasks.all())
        self.assertTrue(agent.agentchecks.all())

        # test site blocking inheritance
        agent.site.block_policy_inheritance = True
        agent.site.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertFalse(agent.autotasks.all())
        self.assertFalse(agent.agentchecks.all())

        agent.site.server_policy = policy
        agent.site.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # should get policies from site policy
        self.assertTrue(agent.autotasks.all())
        self.assertTrue(agent.agentchecks.all())

        # test agent blocking inheritance
        agent.block_policy_inheritance = True
        agent.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        self.assertFalse(agent.autotasks.all())
        self.assertFalse(agent.agentchecks.all())

        agent.policy = policy
        agent.save()

        agent.generate_checks_from_policies()
        agent.generate_tasks_from_policies()

        # should get policies from agent policy
        self.assertTrue(agent.autotasks.all())
        self.assertTrue(agent.agentchecks.all())
