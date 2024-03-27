from unittest.mock import patch

from model_bakery import baker

from agents.models import Agent
from tacticalrmm.constants import AgentMonType
from tacticalrmm.test import TacticalTestCase


class AgentSaveTestCase(TacticalTestCase):
    def setUp(self):
        self.client1 = baker.make("clients.Client")
        self.client2 = baker.make("clients.Client")
        self.site1 = baker.make("clients.Site", client=self.client1)
        self.site2 = baker.make("clients.Site", client=self.client2)
        self.site3 = baker.make("clients.Site", client=self.client2)
        self.agent = baker.make(
            "agents.Agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
        )

    @patch.object(Agent, "set_alert_template")
    def test_set_alert_template_called_on_mon_type_change(
        self, mock_set_alert_template
    ):
        self.agent.monitoring_type = AgentMonType.WORKSTATION
        self.agent.save()
        mock_set_alert_template.assert_called_once()

    @patch.object(Agent, "set_alert_template")
    def test_set_alert_template_called_on_site_change(self, mock_set_alert_template):
        self.agent.site = self.site2
        self.agent.save()
        mock_set_alert_template.assert_called_once()

    @patch.object(Agent, "set_alert_template")
    def test_set_alert_template_called_on_site_and_montype_change(
        self, mock_set_alert_template
    ):
        print(f"before: {self.agent.monitoring_type} site: {self.agent.site_id}")
        self.agent.site = self.site3
        self.agent.monitoring_type = AgentMonType.WORKSTATION
        self.agent.save()
        mock_set_alert_template.assert_called_once()
        print(f"after: {self.agent.monitoring_type} site: {self.agent.site_id}")

    @patch.object(Agent, "set_alert_template")
    def test_set_alert_template_not_called_without_changes(
        self, mock_set_alert_template
    ):
        self.agent.save()
        mock_set_alert_template.assert_not_called()

    @patch.object(Agent, "set_alert_template")
    def test_set_alert_template_not_called_on_non_relevant_field_change(
        self, mock_set_alert_template
    ):
        self.agent.hostname = "abc123"
        self.agent.save()
        mock_set_alert_template.assert_not_called()
