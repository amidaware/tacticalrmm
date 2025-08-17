from itertools import cycle
from unittest.mock import patch

from model_bakery import baker, seq
from django.db.models import Prefetch
from agents.models import Agent
from clients.models import Site
from core.utils import get_core_settings
from tacticalrmm.constants import AgentMonType, TaskSyncStatus
from tacticalrmm.test import TacticalTestCase
from winupdate.models import WinUpdatePolicy

from .serializers import (
    PolicyCheckStatusSerializer,
    PolicyOverviewSerializer,
    PolicySerializer,
    PolicyTaskStatusSerializer,
)


class TestPolicyViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_all_policies(self):
        url = "/automation/policies/"

        baker.make("automation.Policy", _quantity=3)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

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
        checks = self.create_checks(parent=policy)
        tasks = baker.make_recipe("autotasks.task", policy=policy, _quantity=3)

        # assign a task to a check
        tasks[0].assigned_check = checks[0]
        tasks[0].save()  #

        # test copy tasks and checks to another policy
        data = {
            "name": "Test Copy Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False,
            "copyId": policy.pk,
        }

        resp = self.client.post("/automation/policies/", data, format="json")
        self.assertEqual(resp.status_code, 200)

        copied_policy = Policy.objects.get(name=data["name"])

        self.assertEqual(copied_policy.autotasks.count(), 3)
        self.assertEqual(copied_policy.policychecks.count(), 7)

        self.check_not_authenticated("post", url)

    @patch("alerts.tasks.cache_agents_alert_template.delay")
    def test_update_policy(self, cache_alert_template):
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

        alert_template = baker.make("alerts.AlertTemplate")
        data = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "alert_template": alert_template.pk,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        cache_alert_template.assert_called_once()

        self.check_not_authenticated("put", url)

    def test_delete_policy(self):
        # returns 404 for invalid policy pk
        resp = self.client.delete("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # setup data
        policy = baker.make("automation.Policy")

        url = f"/automation/policies/{policy.pk}/"  #

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("delete", url)

    def test_get_policy_check_status(self):
        # setup data
        policy = baker.make("automation.Policy")
        agent = baker.make_recipe("agents.agent", policy=policy)
        policy_diskcheck = baker.make_recipe("checks.diskspace_check", policy=policy)
        result = baker.make(
            "checks.CheckResult", agent=agent, assigned_check=policy_diskcheck
        )

        url = f"/automation/checks/{policy_diskcheck.pk}/status/"

        resp = self.client.get(url, format="json")
        serializer = PolicyCheckStatusSerializer([result], many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

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
        clients = Client.objects.select_related(
            "workstation_policy", "server_policy"
        ).prefetch_related(
            Prefetch(
                "sites",
                queryset=Site.objects.select_related(
                    "workstation_policy", "server_policy"
                ),
                to_attr="filtered_sites",
            )
        )
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

    def test_get_policy_task_status(self):
        # policy with a task
        policy = baker.make("automation.Policy")
        agent = baker.make_recipe("agents.agent", policy=policy)
        task = baker.make_recipe("autotasks.task", policy=policy)
        result = baker.make("autotasks.TaskResult", task=task, agent=agent)

        url = f"/automation/tasks/{task.id}/status/"

        serializer = PolicyTaskStatusSerializer([result], many=True)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.assertEqual(len(resp.data), 1)

        self.check_not_authenticated("get", url)

    @patch("automation.tasks.run_win_policy_autotasks_task.delay")
    def test_run_win_task(self, mock_task):
        policy = baker.make("automation.Policy")
        # create managed policy tasks
        task = baker.make_recipe("autotasks.task", policy=policy)

        url = f"/automation/tasks/{task.id}/run/"
        resp = self.client.post(url, format="json")
        self.assertEqual(resp.status_code, 200)

        mock_task.assert_called_with(task=task.id)

        self.check_not_authenticated("post", url)

    def test_create_new_patch_policy(self):
        url = "/automation/patchpolicy/"

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
        resp = self.client.put("/automation/patchpolicy/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        policy = baker.make("automation.Policy")
        patch_policy = baker.make("winupdate.WinUpdatePolicy", policy=policy)
        url = f"/automation/patchpolicy/{patch_policy.pk}/"

        data = {
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
        url = "/automation/patchpolicy/reset/"

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

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site=sites[0])

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset agents in client
        data = {"client": clients[1].id}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.filter(site__client=clients[1])

        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        # test reset all agents
        data = {}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        agents = Agent.objects.all()
        for agent in agents:
            for k, v in inherit_fields.items():
                self.assertEqual(getattr(agent.winupdatepolicy.get(), k), v)

        self.check_not_authenticated("post", url)

    def test_delete_patch_policy(self):
        # test patch policy doesn't exist
        resp = self.client.delete("/automation/patchpolicy/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        winupdate_policy = baker.make_recipe(
            "winupdate.winupdate_policy", policy__name="Test Policy"
        )
        url = f"/automation/patchpolicy/{winupdate_policy.pk}/"

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
        policy.workstation_clients.add(workstation_agents[13].client)

        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["server_clients"]), 1)
        self.assertEqual(len(resp.data["server_sites"]), 0)
        self.assertEqual(len(resp.data["workstation_clients"]), 1)
        self.assertEqual(len(resp.data["workstation_sites"]), 0)
        self.assertEqual(len(resp.data["agents"]), 0)

        # Add Site to Policy
        policy.server_sites.add(server_agents[10].site)
        policy.workstation_sites.add(workstation_agents[10].site)
        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"
        )
        self.assertEqual(len(resp.data["server_sites"]), 1)
        self.assertEqual(len(resp.data["workstation_sites"]), 1)
        self.assertEqual(len(resp.data["agents"]), 0)

        # Add Agent to Policy
        policy.agents.add(server_agents[2])
        policy.agents.add(workstation_agents[2])
        resp = self.client.get(
            f"/automation/policies/{policy.pk}/related/", format="json"
        )
        self.assertEqual(len(resp.data["agents"]), 2)

    def test_getting_agent_policy_checks(self):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        self.create_checks(parent=policy)
        agent = baker.make_recipe("agents.agent", policy=policy)

        # test policy assigned to agent
        self.assertEqual(len(agent.get_checks_from_policies()), 7)

    def test_getting_agent_policy_checks_with_enforced(self):
        # setup data
        policy = baker.make("automation.Policy", active=True, enforced=True)
        script = baker.make_recipe("scripts.script")
        self.create_checks(parent=policy, script=script)

        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site, policy=policy)
        self.create_checks(parent=agent, script=script)

        overridden_checks = agent.get_checks_with_policies()
        checks = agent.get_checks_with_policies(exclude_overridden=True)

        # make sure each agent check says overridden_by_policy
        self.assertEqual(len(checks), 7)
        self.assertEqual(len(overridden_checks), 14)

    def test_getting_agent_tasks(self):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        tasks = baker.make_recipe(
            "autotasks.task", policy=policy, name=seq("Task"), _quantity=3
        )
        agent = baker.make_recipe("agents.server_agent", policy=policy)

        tasks = agent.get_tasks_from_policies()

        # make sure there are 3 agent tasks
        self.assertEqual(len(tasks), 3)

    @patch("autotasks.models.AutomatedTask.run_win_task")
    def test_run_policy_task(self, run_win_task):
        from .tasks import run_win_policy_autotasks_task

        policy = baker.make("automation.Policy", active=True)
        task = baker.make_recipe("autotasks.task", policy=policy)
        baker.make_recipe("agents.server_agent", policy=policy, _quantity=3)

        run_win_policy_autotasks_task(task=task.id)

        # should run for each agent under the policy
        self.assertEqual(run_win_task.call_count, 3)

    def test_update_policy_tasks(self):
        from autotasks.models import TaskResult

        # setup data
        policy = baker.make("automation.Policy", active=True)
        task = baker.make_recipe("autotasks.task", enabled=True, policy=policy)

        agent = baker.make_recipe("agents.server_agent", policy=policy)
        task_result = baker.make(
            "autotasks.TaskResult",
            task=task,
            agent=agent,
            sync_status=TaskSyncStatus.SYNCED,
        )

        # this change shouldn't trigger the task_result field to sync_status = "notsynced"
        task.actions = {
            "type": "cmd",
            "command": "whoami",
            "timeout": 90,
            "shell": "cmd",
        }
        task.save()

        self.assertEqual(
            TaskResult.objects.get(pk=task_result.id).sync_status, TaskSyncStatus.SYNCED
        )

        # task result should now be "notsynced"
        task.enabled = False
        task.save()
        self.assertEqual(
            TaskResult.objects.get(pk=task_result.id).sync_status,
            TaskSyncStatus.NOT_SYNCED,
        )

    def test_policy_exclusions(self):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        baker.make_recipe("checks.memory_check", policy=policy)
        baker.make_recipe("autotasks.task", policy=policy)
        agent = baker.make_recipe(
            "agents.agent", policy=policy, monitoring_type=AgentMonType.SERVER
        )

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(len(tasks), 1)

        # add agent to policy exclusions
        policy.excluded_agents.set([agent])

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertEqual(policy.related_agents().count(), 0)
        self.assertEqual(len(checks), 0)
        self.assertEqual(len(tasks), 0)

        # delete agent tasks
        policy.excluded_agents.clear()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(len(tasks), 1)

        # add policy exclusions to site
        policy.excluded_sites.set([agent.site])

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertEqual(policy.related_agents().count(), 0)
        self.assertEqual(len(checks), 0)
        self.assertEqual(len(tasks), 0)

        # delete agent tasks and reset
        policy.excluded_sites.clear()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(len(tasks), 1)

        # add policy exclusions to client
        policy.excluded_clients.set([agent.client])

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertEqual(policy.related_agents().count(), 0)
        self.assertEqual(len(checks), 0)
        self.assertEqual(len(tasks), 0)

        # delete agent tasks and reset
        policy.excluded_clients.clear()
        agent.policy = None
        agent.save()

        # test on default policy
        core = get_core_settings()
        core.server_policy = policy
        core.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # make sure related agents on policy returns correctly
        self.assertEqual(policy.related_agents().count(), 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(len(tasks), 1)

        # add policy exclusions to client
        policy.excluded_clients.set([agent.client])

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertEqual(policy.related_agents().count(), 0)
        self.assertEqual(len(checks), 0)
        self.assertEqual(len(tasks), 0)

    def test_policy_inheritance_blocking(self):
        # setup data
        policy = baker.make("automation.Policy", active=True)
        baker.make_recipe("checks.memory_check", policy=policy)
        baker.make_recipe("autotasks.task", policy=policy)
        agent = baker.make_recipe("agents.agent", monitoring_type=AgentMonType.SERVER)

        core = get_core_settings()
        core.server_policy = policy
        core.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # should get policies from default policy
        self.assertTrue(checks)
        self.assertTrue(tasks)

        # test client blocking inheritance
        agent.site.client.block_policy_inheritance = True
        agent.site.client.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertFalse(checks)
        self.assertFalse(tasks)

        agent.site.client.server_policy = policy
        agent.site.client.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # should get policies from client policy
        self.assertTrue(tasks)
        self.assertTrue(checks)

        # test site blocking inheritance
        agent.site.block_policy_inheritance = True
        agent.site.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertFalse(tasks)
        self.assertFalse(checks)

        agent.site.server_policy = policy
        agent.site.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # should get policies from site policy
        self.assertTrue(tasks)
        self.assertTrue(checks)

        # test agent blocking inheritance
        agent.block_policy_inheritance = True
        agent.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        self.assertFalse(tasks)
        self.assertFalse(checks)

        agent.policy = policy
        agent.save()

        checks = agent.get_checks_with_policies()
        tasks = agent.get_tasks_with_policies()

        # should get policies from agent policy
        self.assertTrue(tasks)
        self.assertTrue(checks)
