from djangormm.test import BaseTestCase


class TestAgentViews(BaseTestCase):

    def test_agents_list_GET(self):
        response = self.client.get("/agents/listagents/")
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        response = self.client.get("/agents/listagents/")
        self.assertEqual(response.status_code, 401)

    def test_agents_agent_detail_GET(self):
        response = self.client.get(f"/agents/{self.agent.pk}/agentdetail/")
        self.assertEqual(response.status_code, 200)