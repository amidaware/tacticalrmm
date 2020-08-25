from rest_framework import status
from django.urls import reverse

from unittest.mock import patch
from tacticalrmm.test import BaseTestCase

from .serializers import (
    PolicyTableSerializer,
    PolicySerializer,
    AutoTaskPolicySerializer,
    PolicyOverviewSerializer,
    PolicyCheckStatusSerializer,
)

from checks.serializers import CheckSerializer

from automation.models import Policy
from checks.models import Check
from autotasks.models import AutomatedTask
from clients.models import Client, Site


class TestPolicyViews(BaseTestCase):
    def test_get_all_policies(self):
        url = "/automation/policies/"

        resp = self.client.get(url, format="json")
        serializer = PolicyTableSerializer([self.policy], many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_get_policy(self):
        url = f"/automation/policies/{self.policy.pk}/"

        resp = self.client.get(url, format="json")
        serializer = PolicySerializer(self.policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # returns 404 for invalid policy pk
        resp = self.client.get("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        self.check_not_authenticated("get", "/automation/policies/500/")

    def test_add_policy(self):
        url = "/automation/policies/"

        valid_payload = {
            "name": "Test Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False,
        }

        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # running again should fail since names are unique
        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch("automation.tasks.generate_agent_checks_from_policies_task.delay")
    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    def test_update_policy(self, mock_tasks_task, mock_checks_task):
        url = f"/automation/policies/{self.policy.pk}/"

        valid_payload = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": True,
            "enforced": False,
        }

        resp = self.client.put(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # only called if active or enforced are updated
        mock_checks_task.assert_not_called()
        mock_tasks_task.assert_not_called()

        valid_payload = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": False,
            "enforced": False,
        }

        resp = self.client.put(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_task.assert_called_with(policypk=self.policy.pk, clear=True)
        mock_tasks_task.assert_called_with(policypk=self.policy.pk, clear=True)

        self.check_not_authenticated("put", url)

    @patch("automation.tasks.generate_agent_checks_from_policies_task.delay")
    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    def test_delete_policy(self, mock_tasks_task, mock_checks_task):
        url = f"/automation/policies/{self.policy.pk}/"

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        mock_checks_task.assert_called_with(policypk=self.policy.pk, clear=True)
        mock_tasks_task.assert_called_with(policypk=self.policy.pk, clear=True)

        self.check_not_authenticated("delete", url)

    def test_get_all_policy_tasks(self):
        url = f"/automation/{self.policy.pk}/policyautomatedtasks/"

        resp = self.client.get(url, format="json")
        serializer = AutoTaskPolicySerializer(self.policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_get_all_policy_checks(self):
        url = f"/automation/{self.policy.pk}/policychecks/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer([self.policyDiskCheck], many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_get_policy_check_status(self):
        url = f"/automation/policycheckstatus/{self.policyDiskCheck.pk}/check/"

        # create managed policy check
        self.policyDiskCheck.create_policy_check(self.agent)

        # see if managed policy check exists
        checks = Check.objects.filter(parent_check=self.policyDiskCheck.pk)
        self.assertTrue(checks.exists())

        resp = self.client.patch(url, format="json")
        serializer = PolicyCheckStatusSerializer(checks, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("patch", url)

    def test_policy_overview(self):
        url = "/automation/policies/overview/"

        clients = Client.objects.all()

        resp = self.client.get(url, format="json")
        serializer = PolicyOverviewSerializer(clients, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_get_related(self):
        url = f"/automation/policies/{self.policy.pk}/related/"

        resp = self.client.get(url, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data["clients"], type([]))
        self.assertIsInstance(resp.data["sites"], type([]))
        self.assertIsInstance(resp.data["agents"], type([]))

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.generate_checks_from_policies")
    @patch("automation.tasks.generate_agent_checks_by_location_task.delay")
    @patch("agents.models.Agent.generate_tasks_from_policies")
    @patch("automation.tasks.generate_agent_tasks_by_location_task.delay")
    def test_update_policy_add(self, mock_tasks_location_task, mock_tasks_task, mock_checks_location_task, mock_checks_task):
        url = f"/automation/related/"

        # data setup
        policy = Policy.objects.create(name="Test Policy")
        client = Client.objects.create(client="Test Client")
        site = Site.objects.create(client=client, site="Test Site")

        # test add client to policy
        client_payload = {"type": "client", "pk": client.pk, "policy": policy.pk}

        # test add site to policy
        site_payload = {"type": "site", "pk": site.pk, "policy": policy.pk}

        # test add agent to policy
        agent_payload = {"type": "agent", "pk": self.agent.pk, "policy": policy.pk}

        # test client add
        resp = self.client.post(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        
        # called because the relation changed
        mock_checks_location_task.assert_called_with(location={"client": client.client}, clear=True)
        mock_checks_location_task.reset_mock()

        mock_tasks_location_task.assert_called_with(location={"client": client.client}, clear=True)
        mock_tasks_location_task.reset_mock()

        # test site add
        resp = self.client.post(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site}, clear=True
        )
        mock_checks_location_task.reset_mock()
        
        mock_tasks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site}, clear=True
        )
        mock_tasks_location_task.reset_mock()

        # test agent add
        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_task.assert_called_with(clear=True)
        mock_checks_task.reset_mock()

        mock_tasks_task.assert_called_with(clear=True)
        mock_tasks_task.reset_mock()

        # Adding the same relations shouldn't trigger mocks
        resp = self.client.post(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_location_task.assert_not_called()
        mock_tasks_location_task.assert_not_called()

        resp = self.client.post(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_checks_location_task.assert_not_called()
        mock_tasks_location_task.assert_not_called()

        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_task.assert_not_called()
        mock_tasks_task.assert_not_called()

        # test remove client from policy
        client_payload = {"type": "client", "pk": client.pk, "policy": 0}

        # test remove site from policy
        site_payload = {"type": "site", "pk": site.pk, "policy": 0}

        # test remove agent from policy
        agent_payload = {"type": "agent", "pk": self.agent.pk, "policy": 0}

        # test client remove
        resp = self.client.post(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(location={"client": client.client}, clear=True)
        mock_checks_location_task.reset_mock()

        mock_tasks_location_task.assert_called_with(location={"client": client.client}, clear=True)
        mock_tasks_location_task.reset_mock()

        # test site remove
        resp = self.client.post(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # called because the relation changed
        mock_checks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site}, clear=True
        )
        mock_checks_location_task.reset_mock()

        mock_tasks_location_task.assert_called_with(
            location={"client": site.client.client, "site": site.site}, clear=True
        )
        mock_tasks_location_task.reset_mock()

        # test agent remove
        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        # called because the relation changed
        mock_checks_task.assert_called_with(clear=True)
        mock_checks_task.reset_mock()

        mock_tasks_task.assert_called_with(clear=True)
        mock_tasks_task.reset_mock()

        # adding the same relations shouldn't trigger mocks
        resp = self.client.post(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_location_task.assert_not_called()
        mock_tasks_location_task.assert_not_called()

        resp = self.client.post(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_location_task.assert_not_called()
        mock_tasks_location_task.assert_not_called()

        resp = self.client.post(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # shouldn't be called since nothing changed
        mock_checks_task.assert_not_called()
        mock_tasks_task.assert_not_called()

        self.check_not_authenticated("post", url)

    def test_relation_by_type(self):
        url = f"/automation/related/"

        # data setup
        policy = Policy.objects.create(name="Test Policy")
        client = Client.objects.create(client="Test Client")
        site = Site.objects.create(client=client, site="Test Site")

        policy.clients.add(client)
        policy.sites.add(site)
        policy.agents.add(self.agent)

        client_payload = {"type": "client", "pk": client.pk}

        # test add site to policy
        site_payload = {"type": "site", "pk": site.pk}

        # test add agent to policy
        agent_payload = {"type": "agent", "pk": self.agent.pk}

        # test client relation get
        serializer = PolicySerializer(policy)
        resp = self.client.patch(url, client_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # test site relation get
        serializer = PolicySerializer(policy)
        resp = self.client.patch(url, site_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # test agent relation get
        serializer = PolicySerializer(policy)
        resp = self.client.patch(url, agent_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        invalid_payload = {"type": "bad_type", "pk": 5}

        resp = self.client.patch(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("patch", url)


class TestPolicyTasks(BaseTestCase):

    def test_policy_related(self):

        # Generates 5 clients with 5 sites each with 5 agents each
        self.generate_agents(5, 5, 5)

        agent = self.agents[50]
        client = Client.objects.get(client=agent.client)
        site = Site.objects.get(client=client, site=agent.site)

        policy = Policy.objects.create(
            name="Policy Relate Tests", desc="my awesome policy", active=True,
        )

        # Add Client to Policy
        policy.clients.add(client)

        resp = self.client.get(f"/automation/policies/{policy.pk}/related/", format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEquals(len(resp.data["clients"]), 1)
        self.assertEquals(len(resp.data["sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 25)
        
        # Add Site to Policy and the agents and sites length shouldn't change
        policy.sites.add(site)
        self.assertEquals(len(resp.data["sites"]), 5)
        self.assertEquals(len(resp.data["agents"]), 25)

        # Add Agent to Policy and the agents length shouldn't change
        policy.agents.add(agent)
        self.assertEquals(len(resp.data["agents"]), 25)
