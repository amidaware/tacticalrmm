from unittest.mock import patch, AsyncMock
from django.urls import reverse
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase
from agents.models import Agent


class BaseRegistryAPITest(TacticalTestCase):
    """Base setup for all registry-related API tests."""

    api_name = None

    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.agent = baker.make(Agent)

        if not self.api_name:
            raise ValueError("Subclasses must define api_name")

        self.url = reverse(self.api_name, args=[self.agent.agent_id])


# Browse Registry Key Test Cases
class TestBrowseRegistry(BaseRegistryAPITest):
    api_name = "browse_registry"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_browse_registry_success(self, mock_nats_cmd) -> None:
        """Should return registry data when agent responds successfully."""
        mock_nats_cmd.return_value = {
            "path": "Computer\\HKEY_LOCAL_MACHINE",
            "subkeys": ["Software", "System"],
            "values": [{"name": "TestValue", "type": "REG_SZ", "data": "Hello"}],
            "has_more": False,
        }

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("subkeys", response.json())
        mock_nats_cmd.assert_called_once()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_browse_registry_timeout(self, mock_nats_cmd) -> None:
        """Should return error if agent times out."""
        mock_nats_cmd.return_value = "timeout"

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_browse_registry_error_from_agent(self, mock_nats_cmd) -> None:
        """Should handle error messages returned by the agent."""
        mock_nats_cmd.return_value = {"error": "Registry path not found"}

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path not found", response.json())

    def test_browse_registry_invalid_agent(self) -> None:
        """Should return 404 if agent does not exist."""
        invalid_url = reverse("browse_registry", args=["A" * 22])
        response = self.client.get(invalid_url, format="json")
        self.assertEqual(response.status_code, 404)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_browse_registry_default_params(self, mock_nats_cmd) -> None:
        """Should use default params if path, page, or page_size not provided."""
        mock_nats_cmd.return_value = {
            "path": "Computer",
            "subkeys": [],
            "values": [],
            "has_more": False,
        }

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        mock_nats_cmd.assert_called_once_with(
            {
                "func": "registry_browse",
                "payload": {"path": "Computer", "page": "1", "page_size": "200"},
            },
            timeout=30,
        )

        # Auth check
        self.check_not_authenticated("get", self.url)


# Create Registry Key Test Cases
class TestCreateRegistry(BaseRegistryAPITest):
    api_name = "create_registry_key"

    def test_create_registry_key_missing_path(self) -> None:
        """Should return error if 'path' is missing or empty."""
        response = self.client.post(self.url, data={}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_key_success(self, mock_nats_cmd) -> None:
        """Should create registry key successfully when agent responds."""
        mock_nats_cmd.return_value = {"status": "ok"}

        data = {"path": "HKEY_LOCAL_MACHINE\\Software\\NewKey"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["path"], data["path"])

        mock_nats_cmd.assert_called_once_with(
            {
                "func": "registry_create_key",
                "payload": {"path": data["path"]},
            },
            timeout=30,
        )

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_key_timeout(self, mock_nats_cmd) -> None:
        """Should handle agent timeout correctly."""
        mock_nats_cmd.return_value = "timeout"
        response = self.client.post(
            self.url,
            {"path": "HKEY_LOCAL_MACHINE\\Software\\TimeoutKey"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_key_agent_error(self, mock_nats_cmd) -> None:
        """Should handle error response from agent."""
        mock_nats_cmd.return_value = {"error": "Access denied"}
        response = self.client.post(
            self.url, {"path": "HKEY_LOCAL_MACHINE\\Software\\DeniedKey"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Access denied", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_key_nats_exception(self, mock_nats_cmd: AsyncMock) -> None:
        """Should handle NATS communication exception."""
        mock_nats_cmd.side_effect = Exception("Connection refused")

        response = self.client.post(
            self.url, {"path": "HKEY_LOCAL_MACHINE\\Software\\ErrorKey"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("NATS communication failed", response.json())

    def test_create_registry_key_invalid_agent(self) -> None:
        """Should return 404 for invalid agent ID."""
        invalid_url = reverse("create_registry_key", args=["A" * 22])
        response = self.client.post(
            invalid_url, {"path": "Computer\\Test"}, format="json"
        )
        self.assertEqual(response.status_code, 404)


# Delete Registry Key Test Cases
class TestDeleteRegistryKey(BaseRegistryAPITest):
    api_name = "delete_registry_key"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_registry_key_success(self, mock_nats):
        """Should delete registry key successfully."""
        mock_nats.return_value = {"status": "success"}
        response = self.client.delete(f"{self.url}?path=HKLM\\Test", format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_delete_registry_key_missing_path(self):
        """Should return error if path query param is missing."""
        response = self.client.delete(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_registry_key_nats_failure(self, mock_nats: AsyncMock) -> None:
        """Should handle NATS exception properly."""
        mock_nats.side_effect = Exception("NATS fail")

        response = self.client.delete(f"{self.url}?path=HKLM\\Test", format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("NATS communication failed", response.json())


# Rename Registry Key Test Cases
class TestRenameRegistryKey(BaseRegistryAPITest):
    api_name = "rename_registry_key"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_rename_registry_key_success(self, mock_nats):
        """Should rename registry key successfully."""
        mock_nats.return_value = {"status": "success"}
        data = {"old_path": "HKLM\\TestOld", "new_path": "HKLM\\TestNew"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_rename_registry_key_missing_paths(self):
        """Should return error when required fields are missing."""
        data = {"old_path": "", "new_path": ""}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Both 'old_path' and 'new_path' are required", response.json())

    def test_rename_registry_key_same_paths(self):
        """Should return error when old and new path are identical."""
        data = {"old_path": "HKLM\\Same", "new_path": "HKLM\\Same"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Old and new path cannot be the same", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_rename_registry_key_nats_failure(self, mock_nats: AsyncMock) -> None:
        """Should handle NATS communication error gracefully."""
        mock_nats.side_effect = Exception("NATS down")

        data = {"old_path": "HKLM\\A", "new_path": "HKLM\\B"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("NATS communication failed", response.json())


# Create Registry Value Test Cases
class TestCreateRegistryValue(BaseRegistryAPITest):
    api_name = "create_registry_value"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_value_success(self, mock_nats):
        """Should create registry value successfully."""
        mock_nats.return_value = {"name": "MyValue", "type": "STRING"}
        data = {"path": "HKLM\\Test", "name": "MyValue", "type": "STRING"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_create_registry_value_missing_fields(self):
        """Should return error if required fields are missing."""
        response = self.client.post(
            self.url, {"path": "", "name": "", "type": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_registry_value_agent_error(self, mock_nats):
        """Should handle error from agent."""
        mock_nats.return_value = {"error": "Access denied"}
        data = {"path": "HKLM\\Test", "name": "Key", "type": "STRING"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Access denied", response.json())


# Delete Registry Value Test Cases
class TestDeleteRegistryValue(BaseRegistryAPITest):
    api_name = "delete_registry_value"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_registry_value_success(self, mock_nats):
        """Should delete registry value successfully."""
        mock_nats.return_value = {"status": "success"}
        url = f"{self.url}?path=HKLM\\Test&name=MyValue"
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_delete_registry_value_missing_params(self):
        """Should return error if params missing."""
        response = self.client.delete(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_registry_value_agent_error(self, mock_nats):
        """Should handle agent error gracefully."""
        mock_nats.return_value = {"error": "Value not found"}
        url = f"{self.url}?path=HKLM\\Test&name=MyValue"
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Value not found", response.json())


# Rename Registry Value Test Cases
class TestRenameRegistryValue(BaseRegistryAPITest):
    api_name = "rename_registry_value"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_rename_registry_value_success(self, mock_nats):
        """Should rename registry value successfully."""
        mock_nats.return_value = {"status": "success", "new_name": "NewVal"}
        data = {"path": "HKLM\\Test", "old_name": "OldVal", "new_name": "NewVal"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_rename_registry_value_missing_fields(self):
        """Should return error if required fields missing."""
        response = self.client.post(
            self.url, {"path": "", "old_name": "", "new_name": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_rename_registry_value_agent_error(self, mock_nats):
        """Should handle agent-side error."""
        mock_nats.return_value = {"error": "Permission denied"}
        data = {"path": "HKLM\\Test", "old_name": "Old", "new_name": "New"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Permission denied", response.json())


# Modify Registry Value Test Cases
class TestModifyRegistryValue(BaseRegistryAPITest):
    api_name = "modify_registry_value"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_modify_registry_value_success(self, mock_nats):
        """Should modify registry value successfully."""
        mock_nats.return_value = {"name": "Key", "type": "STRING", "data": "Updated"}
        data = {
            "path": "HKLM\\Test",
            "name": "Key",
            "type": "STRING",
            "data": "Updated",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_modify_registry_value_missing_fields(self):
        """Should return error if required fields missing."""
        response = self.client.post(
            self.url, {"path": "", "name": "", "type": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Registry path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_modify_registry_value_agent_error(self, mock_nats):
        """Should handle agent-side modify error."""
        mock_nats.return_value = {"error": "Cannot modify key"}
        data = {
            "path": "HKLM\\Test",
            "name": "Key",
            "type": "STRING",
            "data": "Updated",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cannot modify key", response.json())
