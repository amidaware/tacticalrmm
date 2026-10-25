import datetime as dt
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone as djangotime
from model_bakery import baker
from rest_framework import status

from agents.models import Agent, FileTransferSession
from logs.models import AuditLog
from tacticalrmm.constants import (
    AgentPlat,
    FILE_BROWSER_DEFAULT_PAGE_SIZE,
    FILE_BROWSER_MAX_PAGE,
    FILE_BROWSER_MAX_PAGE_SIZE,
    FILE_BROWSER_MIN_AGENT_VERSION,
    FILE_TRANSFER_CHUNK_SIZE,
    FILE_TRANSFER_IDLE_EXPIRE_MINUTES,
    FILE_TRANSFER_MAX_SESSIONS_PER_AGENT,
    FILE_TRANSFER_MAX_SESSIONS_PER_USER,
    FILE_TRANSFER_PIPELINE_DEPTH,
    AuditActionType,
    FileTransferConflictPolicy,
    FileTransferOperation,
    FileTransferStatus,
)
from tacticalrmm.helpers import notify_error
from tacticalrmm.test import TacticalTestCase


class BaseFileBrowserAPITest(TacticalTestCase):
    """Base setup for File Browser and file-transfer API tests."""

    api_name = None

    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.agent = baker.make(
            Agent,
            version="2.12.0",
            plat="windows",
            agent_id="filebrowser-test-agent-id-0001",
            last_seen=djangotime.now(),
        )
        if self.api_name:
            self.url = reverse(self.api_name, args=[self.agent.agent_id])

    def _session_url(self, api_name: str, session_id) -> str:
        return reverse(api_name, args=[self.agent.agent_id, session_id])

    def _make_transfer_session(self, **kwargs) -> FileTransferSession:
        defaults = {
            "agent": self.agent,
            "user": self.john,
            "operation": FileTransferOperation.UPLOAD,
            "status": FileTransferStatus.TRANSFERRING,
            "destination_path": r"C:\Users\Public\demo.txt",
            "filename": "demo.txt",
            "conflict_policy": FileTransferConflictPolicy.REPLACE,
            "total_size": 1024,
            "chunk_size": FILE_TRANSFER_CHUNK_SIZE,
            "committed_offset": 0,
            "expires_at": djangotime.now() + dt.timedelta(hours=1),
        }
        defaults.update(kwargs)
        return FileTransferSession.objects.create(**defaults)

    def _fill_agent_session_cap(self) -> None:
        for i in range(FILE_TRANSFER_MAX_SESSIONS_PER_AGENT):
            self._make_transfer_session(
                filename=f"cap-{i}.txt",
                destination_path=rf"C:\Users\Public\cap-{i}.txt",
            )

    def _fill_user_session_cap(self) -> None:
        for i in range(FILE_TRANSFER_MAX_SESSIONS_PER_USER):
            other = baker.make(Agent, version="2.12.0", plat="windows")
            self._make_transfer_session(
                agent=other,
                filename=f"user-cap-{i}.txt",
                destination_path=rf"C:\Users\Public\user-cap-{i}.txt",
            )


class TestListFiles(BaseFileBrowserAPITest):
    api_name = "list_files"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_success(self, mock_nats_cmd) -> None:
        """Should return normalized directory listing when agent responds."""
        mock_nats_cmd.return_value = {
            "path": r"C:\Users\Public",
            "items": [
                {
                    "id": r"C:\Users\Public\Docs",
                    "name": "Docs",
                    "path": r"C:\Users\Public\Docs",
                    "type": "folder",
                    "size": "0",
                    "modified": "2026-06-18T12:00:00Z",
                },
                {
                    "name": "readme.txt",
                    "path": r"C:\Users\Public\readme.txt",
                    "type": "file",
                    "size": "12",
                    "extension": "txt",
                },
            ],
            "has_more": False,
            "total": 2,
        }

        response = self.client.get(
            self.url,
            {"path": r"C:\Users\Public"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["path"], r"C:\Users\Public")
        self.assertEqual(len(body["items"]), 2)
        self.assertEqual(body["items"][0]["type"], "folder")
        self.assertEqual(body["items"][1]["extension"], "txt")
        self.assertFalse(body["has_more"])
        self.assertEqual(body["total"], 2)
        mock_nats_cmd.assert_called_once()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_forwards_canonical_windows_path(self, mock_nats_cmd) -> None:
        drive_root = "C:\\"
        mock_nats_cmd.return_value = {
            "path": drive_root,
            "items": [],
            "has_more": False,
            "total": 0,
        }
        response = self.client.get(self.url, {"path": "C:"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["payload"]["path"],
            drive_root,
        )

        mock_nats_cmd.reset_mock()
        mock_nats_cmd.return_value = {
            "path": r"C:\Users\Public",
            "items": [],
            "has_more": False,
            "total": 0,
        }
        response = self.client.get(self.url, {"path": "C:/Users/Public"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["payload"]["path"],
            r"C:\Users\Public",
        )

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_posix_strips_trailing_slash(self, mock_nats_cmd) -> None:
        self.agent.plat = "linux"
        self.agent.save(update_fields=["plat"])
        mock_nats_cmd.return_value = {
            "path": "/tmp/foo",
            "items": [],
            "has_more": False,
            "total": 0,
        }
        response = self.client.get(self.url, {"path": "/tmp/foo/"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["payload"]["path"],
            "/tmp/foo",
        )

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_default_path_and_pagination(self, mock_nats_cmd) -> None:
        """Empty path on page 1 should ask the agent for its default browse root."""
        mock_nats_cmd.return_value = {
            "path": r"C:\Users\Public",
            "items": [],
            "has_more": False,
            "total": 0,
        }

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["path"], r"C:\Users\Public")
        mock_nats_cmd.assert_called_once_with(
            {
                "func": "files_list",
                "payload": {
                    "path": "",
                    "page": "1",
                    "page_size": str(FILE_BROWSER_DEFAULT_PAGE_SIZE),
                },
            },
            timeout=30,
        )

        self.check_not_authenticated("get", self.url)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_with_filter(self, mock_nats_cmd) -> None:
        """Should pass sanitized name filter through to the agent."""
        mock_nats_cmd.return_value = {
            "path": r"C:\Users\Public",
            "items": [],
            "has_more": False,
            "total": 0,
        }

        response = self.client.get(
            self.url,
            {
                "path": r"C:\Users\Public",
                "filter": "readme",
                "page": 1,
                "page_size": 50,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_nats_cmd.assert_called_once_with(
            {
                "func": "files_list",
                "payload": {
                    "path": r"C:\Users\Public",
                    "page": "1",
                    "page_size": "50",
                    "filter": "readme",
                },
            },
            timeout=30,
        )

    def test_list_files_empty_path_requires_page_one(self) -> None:
        """Empty path is only allowed for page 1 (agent-resolved default)."""
        response = self.client.get(self.url, {"page": 2}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("path is required", response.json())

    def test_list_files_invalid_page_size(self) -> None:
        """Should reject page_size outside the allowed range."""
        response = self.client.get(
            self.url,
            {
                "path": r"C:\Users\Public",
                "page_size": FILE_BROWSER_MAX_PAGE_SIZE + 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("page_size must be between 1 and", response.json())

    def test_list_files_invalid_page(self) -> None:
        """Should reject page values that can overflow agent pagination math."""
        response = self.client.get(
            self.url,
            {
                "path": r"C:\Users\Public",
                "page": FILE_BROWSER_MAX_PAGE + 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("page must be between 1 and", response.json())

    def test_list_files_invalid_filter_chars(self) -> None:
        """Should reject filters containing control characters."""
        response = self.client.get(
            self.url,
            {"path": r"C:\Users\Public", "filter": "bad\nfilter"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("filter contains invalid characters", response.json())

    def test_list_files_invalid_path(self) -> None:
        """Should reject relative / traversal paths before contacting the agent."""
        response = self.client.get(
            self.url,
            {"path": r"Users\Public"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("absolute Windows path", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_timeout(self, mock_nats_cmd) -> None:
        """Should return error if agent times out."""
        mock_nats_cmd.return_value = "timeout"
        response = self.client.get(
            self.url, {"path": r"C:\Users\Public"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_natsdown(self, mock_nats_cmd) -> None:
        """NATS connect failure must return error."""
        mock_nats_cmd.return_value = "natsdown"
        response = self.client.get(
            self.url, {"path": r"C:\Users\Public"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_error_from_agent(self, mock_nats_cmd) -> None:
        """Should surface agent error messages."""
        mock_nats_cmd.return_value = {"error": "Access denied"}
        response = self.client.get(
            self.url, {"path": r"C:\Users\Public"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Access denied", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_missing_resolved_path(self, mock_nats_cmd) -> None:
        """Agent must return a browsable path when the client sent an empty path."""
        mock_nats_cmd.return_value = {"items": [], "has_more": False, "total": 0}
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Agent did not return a browsable path", response.json())

    def test_list_files_invalid_agent(self) -> None:
        """Should return 404 if agent does not exist."""
        invalid_url = reverse("list_files", args=["A" * 22])
        response = self.client.get(invalid_url, format="json")
        self.assertEqual(response.status_code, 404)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_list_files_old_agent_version(self, mock_nats_cmd) -> None:
        """Agents below 2.12.0 must return 400 immediately, not wait on unknown NATS funcs."""
        self.agent.version = "2.11.9"
        self.agent.save(update_fields=["version"])
        response = self.client.get(
            self.url, {"path": r"C:\Users\Public"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(FILE_BROWSER_MIN_AGENT_VERSION, response.json())
        mock_nats_cmd.assert_not_called()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_files_success(self, mock_nats_cmd) -> None:
        """DELETE on files/ should delete paths and return per-path results."""
        mock_nats_cmd.return_value = {
            "results": [
                {"path": r"C:\Users\Public\old.txt", "success": True},
                {
                    "path": r"C:\Users\Public\locked.txt",
                    "success": False,
                    "error": "Access denied",
                },
            ]
        }

        response = self.client.delete(
            self.url,
            {
                "paths": [
                    r"C:\Users\Public\old.txt",
                    r"C:\Users\Public\locked.txt",
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(len(body["results"]), 2)
        self.assertTrue(body["results"][0]["success"])
        self.assertFalse(body["results"][1]["success"])
        mock_nats_cmd.assert_called_once()
        call_args = mock_nats_cmd.call_args[0][0]
        self.assertEqual(call_args["func"], "files_delete")
        log = AuditLog.objects.get(action=AuditActionType.DELETE)
        self.assertEqual(log.after_value["operation"], "delete")
        self.assertEqual(len(log.after_value["paths"]), 2)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_files_forwards_canonical_windows_paths(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {
            "results": [{"path": r"C:\Users\Public\old.txt", "success": True}]
        }
        response = self.client.delete(
            self.url,
            {"paths": ["C:/Users/Public/old.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        sent = json.loads(mock_nats_cmd.call_args[0][0]["payload"]["paths"])
        self.assertEqual(sent, [r"C:\Users\Public\old.txt"])

    def test_delete_files_missing_paths(self) -> None:
        """Should require a non-empty paths list."""
        response = self.client.delete(self.url, {"paths": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paths is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_delete_files_nats_exception(self, mock_nats_cmd: AsyncMock) -> None:
        """Should handle NATS communication exception."""
        mock_nats_cmd.side_effect = Exception("Connection refused")
        response = self.client.delete(
            self.url,
            {"paths": [r"C:\Users\Public\old.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("NATS communication failed", response.json())


class TestCheckFileExists(BaseFileBrowserAPITest):
    api_name = "check_file_exists"

    def test_exists_missing_path(self) -> None:
        response = self.client.post(self.url, {"names": ["a.txt"]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("path is required", response.json())

    def test_exists_names_must_be_list(self) -> None:
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "names": "a.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("names must be a list", response.json())

    def test_exists_rejects_path_in_name(self) -> None:
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "names": ["bad\\name.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_exists_success(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"existing": ["readme.txt"]}
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "names": ["readme.txt", "new.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["existing"], ["readme.txt"])
        mock_nats_cmd.assert_called_once()
        payload = mock_nats_cmd.call_args[0][0]
        self.assertEqual(payload["func"], "files_exists")
        self.assertEqual(payload["payload"]["path"], r"C:\Users\Public")
        self.assertIn("readme.txt", payload["payload"]["names_json"])

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_exists_forwards_canonical_windows_path(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"existing": []}
        response = self.client.post(
            self.url,
            {"path": "C:/Users/Public", "names": ["readme.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["payload"]["path"],
            r"C:\Users\Public",
        )


class TestGetFileProperties(BaseFileBrowserAPITest):
    api_name = "get_file_properties"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_get_file_properties_success(self, mock_nats_cmd) -> None:
        """Should return normalized properties for a path."""
        mock_nats_cmd.return_value = {
            "name": "Docs",
            "path": r"C:\Users\Public\Docs",
            "type": "folder",
            "size": "0",
            "location": r"C:\Users\Public",
            "file_count": 3,
            "folder_count": 1,
            "summary_truncated": False,
        }

        response = self.client.get(
            self.url, {"path": r"C:\Users\Public\Docs"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Docs")
        self.assertEqual(body["file_count"], 3)
        self.assertEqual(body["folder_count"], 1)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_properties")

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_get_file_properties_forwards_canonical_windows_path(
        self, mock_nats_cmd
    ) -> None:
        mock_nats_cmd.return_value = {
            "name": "Docs",
            "path": r"C:\Users\Public\Docs",
            "type": "folder",
            "size": "0",
        }
        response = self.client.get(
            self.url, {"path": "C:/Users/Public/Docs"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["payload"]["path"],
            r"C:\Users\Public\Docs",
        )

    def test_get_file_properties_missing_path(self) -> None:
        """Should require path query param."""
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("path is required", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_get_file_properties_timeout(self, mock_nats_cmd) -> None:
        """Should handle agent timeout."""
        mock_nats_cmd.return_value = "timeout"
        response = self.client.get(
            self.url, {"path": r"C:\Users\Public\Docs"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())


class TestCreateFileFolder(BaseFileBrowserAPITest):
    api_name = "create_file_folder"

    def test_create_file_folder_missing_path(self) -> None:
        """Should return error if path is missing."""
        response = self.client.post(self.url, {"name": "NewFolder"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("path is required", response.json())

    def test_create_file_folder_invalid_name(self) -> None:
        """Should reject invalid folder names."""
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "name": "bad/name"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_file_folder_success(self, mock_nats_cmd) -> None:
        """Should create folder when agent responds with an item."""
        mock_nats_cmd.return_value = {
            "name": "NewFolder",
            "path": r"C:\Users\Public\NewFolder",
            "type": "folder",
            "size": "0",
        }

        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "name": "NewFolder"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["item"]["name"], "NewFolder")
        mock_nats_cmd.assert_called_once_with(
            {
                "func": "files_mkdir",
                "payload": {"path": r"C:\Users\Public", "name": "NewFolder"},
            },
            timeout=30,
        )
        log = AuditLog.objects.get(action=AuditActionType.ADD)
        self.assertEqual(log.agent_id, self.agent.agent_id)
        self.assertEqual(log.after_value["operation"], "mkdir")
        self.assertIn("ip", log.debug_info)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_file_folder_agent_error(self, mock_nats_cmd) -> None:
        """Should return agent error without the prefixed title (prefix_error=False)."""
        mock_nats_cmd.return_value = {"error": "Folder already exists"}
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "name": "NewFolder"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Folder already exists")
        self.assertFalse(AuditLog.objects.filter(action=AuditActionType.ADD).exists())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_create_file_folder_timeout(self, mock_nats_cmd) -> None:
        """Should handle agent timeout."""
        mock_nats_cmd.return_value = "timeout"
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public", "name": "NewFolder"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to contact the agent", response.json())


class TestRenameFile(BaseFileBrowserAPITest):
    api_name = "rename_file"

    def test_rename_file_missing_path(self) -> None:
        """Should require path."""
        response = self.client.post(
            self.url, {"new_name": "renamed.txt"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("path is required", response.json())

    def test_rename_file_invalid_new_name(self) -> None:
        """Should reject invalid new_name values."""
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public\old.txt", "new_name": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_name", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_rename_file_success(self, mock_nats_cmd) -> None:
        """Should rename when agent returns the updated item."""
        mock_nats_cmd.return_value = {
            "name": "renamed.txt",
            "path": r"C:\Users\Public\renamed.txt",
            "type": "file",
            "size": "10",
            "extension": "txt",
        }

        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public\old.txt", "new_name": "renamed.txt"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["item"]["name"], "renamed.txt")
        mock_nats_cmd.assert_called_once_with(
            {
                "func": "files_rename",
                "payload": {
                    "path": r"C:\Users\Public\old.txt",
                    "new_name": "renamed.txt",
                },
            },
            timeout=30,
        )
        log = AuditLog.objects.get(action=AuditActionType.MODIFY)
        self.assertEqual(log.after_value["operation"], "rename")
        self.assertEqual(log.after_value["new_name"], "renamed.txt")
        """Should handle NATS communication error."""
        mock_nats_cmd.side_effect = Exception("NATS down")
        response = self.client.post(
            self.url,
            {"path": r"C:\Users\Public\old.txt", "new_name": "renamed.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("NATS communication failed", response.json())


class TestInitFileUpload(BaseFileBrowserAPITest):
    api_name = "init_file_upload"

    def _upload_payload(self, **overrides) -> dict:
        data = {
            "filename": "demo.txt",
            "destination_path": r"C:\Users\Public",
            "total_size": 1024,
        }
        data.update(overrides)
        return data

    def test_init_file_upload_missing_filename(self) -> None:
        """Should require a valid filename."""
        response = self.client.post(
            self.url,
            self._upload_payload(filename=""),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("filename", response.json())

    def test_init_file_upload_trailing_period_returns_400(self) -> None:
        """Windows would silently store trail. as trail; reject instead."""
        response = self.client.post(
            self.url,
            self._upload_payload(filename="trail."),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("period", response.json())
        self.assertFalse(FileTransferSession.objects.filter(agent=self.agent).exists())

    def test_init_file_upload_invalid_total_size(self) -> None:
        """Should require a positive total_size."""
        response = self.client.post(
            self.url,
            self._upload_payload(total_size=0),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("total_size must be a positive integer", response.json())

    def test_init_file_upload_invalid_conflict_policy(self) -> None:
        """Should only accept replace or skip."""
        response = self.client.post(
            self.url,
            self._upload_payload(conflict_policy="keep"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("conflict_policy must be 'replace' or 'skip'", response.json())

    def test_init_file_upload_invalid_destination(self) -> None:
        """Should reject non-absolute destination paths."""
        response = self.client.post(
            self.url,
            self._upload_payload(destination_path="Public"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination_path", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_upload_allows_apostrophe_in_path(self, mock_nats_cmd) -> None:
        """Should upload into folders like John's Docs."""
        mock_nats_cmd.return_value = {"status": "ready", "committed_offset": 0}
        response = self.client.post(
            self.url,
            self._upload_payload(
                filename="it's & co.txt",
                destination_path=r"C:\Users\John's Docs",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        session = FileTransferSession.objects.get(
            session_id=response.json()["session_id"]
        )
        self.assertEqual(
            session.destination_path, r"C:\Users\John's Docs\it's & co.txt"
        )

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_upload_success(self, mock_nats_cmd) -> None:
        """Should create a session and return agent-ready offsets."""
        mock_nats_cmd.return_value = {"status": "ready", "committed_offset": 0}

        response = self.client.post(
            self.url,
            self._upload_payload(conflict_policy="skip"),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], FileTransferStatus.AGENT_READY)
        self.assertEqual(body["committed_offset"], 0)
        self.assertEqual(body["chunk_size"], FILE_TRANSFER_CHUNK_SIZE)
        self.assertTrue(body["session_id"])

        session = FileTransferSession.objects.get(session_id=body["session_id"])
        self.assertEqual(session.operation, FileTransferOperation.UPLOAD)
        self.assertEqual(session.conflict_policy, FileTransferConflictPolicy.SKIP)
        self.assertEqual(session.destination_path, r"C:\Users\Public\demo.txt")
        mock_nats_cmd.assert_called_once()
        payload = mock_nats_cmd.call_args[0][0]["payload"]
        self.assertEqual(payload["conflict_policy"], FileTransferConflictPolicy.SKIP)
        self.assertEqual(payload["destination_path"], r"C:\Users\Public\demo.txt")
        log = AuditLog.objects.get(action=AuditActionType.FILE_TRANSFER)
        self.assertEqual(log.after_value["operation"], "upload")
        self.assertEqual(log.after_value["paths"], [r"C:\Users\Public\demo.txt"])

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_upload_agent_error_marks_failed(self, mock_nats_cmd) -> None:
        """Agent prepare failures should mark the session failed."""
        mock_nats_cmd.return_value = {"error": "destination already exists"}
        response = self.client.post(self.url, self._upload_payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination already exists", response.json())
        self.assertEqual(FileTransferSession.objects.count(), 1)
        self.assertEqual(
            FileTransferSession.objects.get().status, FileTransferStatus.FAILED
        )
        funcs = [call[0][0]["func"] for call in mock_nats_cmd.call_args_list]
        self.assertIn("files_upload_prepare", funcs)
        self.assertIn("files_upload_abort", funcs)

    def test_init_file_upload_session_limit_returns_429(self) -> None:
        """Fresh init should 429 when the per-agent concurrency cap is full."""
        self._fill_agent_session_cap()
        response = self.client.post(self.url, self._upload_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Too many concurrent file transfers", response.json())

    def test_init_file_upload_user_session_limit_returns_429(self) -> None:
        """Per user cap must 429 even when this agent is under its own cap."""
        if FILE_TRANSFER_MAX_SESSIONS_PER_USER <= 0:
            self.skipTest("per-user transfer cap is disabled")
        self._fill_user_session_cap()
        response = self.client.post(self.url, self._upload_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("this user", response.json())

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.get_upload_ack", return_value=None)
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_upload_resume_agent_unreachable_is_retryable(
        self, mock_nats_cmd, _mock_ack, _mock_clear
    ) -> None:
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=512,
        )
        mock_nats_cmd.return_value = "timeout"
        response = self.client.post(
            self.url,
            {"session_id": str(session.session_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 408)
        self.assertIn("Unable to contact the agent", response.json())
        self.assertNotIn("timed out waiting for agent to", response.json().lower())
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.get_upload_ack", return_value=None)
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_upload_resume_skips_session_cap(
        self, mock_nats_cmd, _mock_ack, _mock_clear
    ) -> None:
        """Resume of an existing session must not be blocked by the concurrency cap."""
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=512,
        )
        for i in range(FILE_TRANSFER_MAX_SESSIONS_PER_AGENT - 1):
            self._make_transfer_session(
                filename=f"other-{i}.txt",
                destination_path=rf"C:\Users\Public\other-{i}.txt",
            )

        mock_nats_cmd.return_value = {
            "status": "ready",
            "committed_offset": 512,
        }
        response = self.client.post(
            self.url,
            {
                "session_id": str(session.session_id),
                "filename": session.filename,
                "total_size": session.total_size,
                "destination_path": r"C:\Users\Public",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("resumed"))
        self.assertEqual(response.json()["committed_offset"], 512)

    def test_init_file_upload_invalid_session_id_returns_400(self) -> None:
        """Malformed resume session_id must be 400."""
        response = self.client.post(
            self.url,
            self._upload_payload(session_id="not-a-uuid"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session_id", response.json())

    def test_init_file_upload_cannot_resume_other_users_session(self) -> None:
        """Resume stays owner scoped so another user cannot take over the transfer."""
        session = self._make_transfer_session(user=self.alice)
        response = self.client.post(
            self.url,
            {
                "session_id": str(session.session_id),
                "filename": session.filename,
                "total_size": session.total_size,
                "destination_path": r"C:\Users\Public",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_init_file_upload_non_string_filename_does_not_500(self) -> None:
        """Json numbers must not attribute error on .strip()."""
        with patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock) as mock_nats:
            mock_nats.return_value = {"status": "ready", "committed_offset": 0}
            response = self.client.post(
                self.url,
                self._upload_payload(filename=123),
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        session = FileTransferSession.objects.get(
            session_id=response.json()["session_id"]
        )
        self.assertEqual(session.filename, "123")

    def test_init_file_upload_object_filename_returns_400(self) -> None:
        """Structured json is rejected instead of crashing the worker."""
        response = self.client.post(
            self.url,
            self._upload_payload(filename={"name": "demo.txt"}),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("filename", response.json())

    def test_init_file_upload_invalid_chunk_size_returns_400(self) -> None:
        """Non integer chunk_size must be 400."""
        response = self.client.post(
            self.url,
            self._upload_payload(chunk_size="huge"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("chunk_size", response.json())


class TestCancelFileUpload(BaseFileBrowserAPITest):
    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_upload_success(self, mock_nats_cmd, _mock_clear) -> None:
        """Cancel should abort on the agent and mark the session cancelled."""
        session = self._make_transfer_session(status=FileTransferStatus.TRANSFERRING)
        mock_nats_cmd.return_value = {"status": "aborted"}

        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_upload_abort")

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_upload_already_terminal(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Completed sessions should be idempotent without contacting the agent."""
        session = self._make_transfer_session(status=FileTransferStatus.COMPLETED)
        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)
        mock_nats_cmd.assert_not_called()

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_upload_failed_still_aborts(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Failed sessions must still tell the agent to drop the handle or .partial."""
        session = self._make_transfer_session(
            status=FileTransferStatus.FAILED,
            error_message="Upload failed",
        )
        mock_nats_cmd.return_value = {"status": "aborted"}
        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {"reason": "error"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.FAILED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_upload_abort")

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_upload_expired_still_aborts(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Expired sessions must still abort on the agent."""
        session = self._make_transfer_session(status=FileTransferStatus.EXPIRED)
        mock_nats_cmd.return_value = {"status": "aborted"}
        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {"reason": "error"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.EXPIRED)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_upload_abort")

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_upload_skips_nats_when_agent_offline(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Offline cancel must still free the slot without waiting on nats."""
        self.agent.last_seen = djangotime.now() - dt.timedelta(minutes=10)
        self.agent.save(update_fields=["last_seen"])
        session = self._make_transfer_session(status=FileTransferStatus.TRANSFERRING)
        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        mock_nats_cmd.assert_not_called()

    def test_cancel_file_upload_not_found(self) -> None:
        """Unknown session should 404."""
        url = self._session_url("cancel_file_upload", uuid4())
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_cancel_other_users_upload_is_not_found(self) -> None:
        """Cancel stays owner scoped; another user's session is not visible."""
        session = self._make_transfer_session(user=self.alice)
        url = self._session_url("cancel_file_upload", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)


class TestInitFileDownload(BaseFileBrowserAPITest):
    api_name = "init_file_download"

    def test_init_file_download_invalid_source(self) -> None:
        """Should reject non-absolute source paths."""
        response = self.client.post(
            self.url, {"source_path": "readme.txt"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("source_path", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_download_allows_apostrophe_in_path(self, mock_nats_cmd) -> None:
        """Should download files from folders like John's Docs."""
        mock_nats_cmd.return_value = {"status": "ready", "total_size": 2048}
        response = self.client.post(
            self.url,
            {"source_path": r"C:\Users\John's Docs\it's & co.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        session = FileTransferSession.objects.get(
            session_id=response.json()["session_id"]
        )
        self.assertEqual(
            session.destination_path, r"C:\Users\John's Docs\it's & co.txt"
        )

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_download_success(self, mock_nats_cmd) -> None:
        """Should create a download session when agent reports ready + size."""
        mock_nats_cmd.return_value = {"status": "ready", "total_size": 2048}

        response = self.client.post(
            self.url,
            {"source_path": r"C:\Users\Public\readme.txt"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], FileTransferStatus.AGENT_READY)
        self.assertEqual(body["total_size"], 2048)
        self.assertEqual(body["committed_offset"], 0)

        session = FileTransferSession.objects.get(session_id=body["session_id"])
        self.assertEqual(session.operation, FileTransferOperation.DOWNLOAD)
        self.assertEqual(session.filename, "readme.txt")
        mock_nats_cmd.assert_called_once()
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["func"], "files_download_prepare"
        )
        log = AuditLog.objects.get(action=AuditActionType.FILE_TRANSFER)
        self.assertEqual(log.after_value["operation"], "download")
        self.assertEqual(log.after_value["paths"], [r"C:\Users\Public\readme.txt"])

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_download_empty_file(self, mock_nats_cmd) -> None:
        """Agent reporting empty/invalid size should fail the session."""
        mock_nats_cmd.return_value = {"status": "ready", "total_size": 0}
        response = self.client.post(
            self.url,
            {"source_path": r"C:\Users\Public\empty.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty or invalid file", response.json())
        self.assertEqual(
            FileTransferSession.objects.get().status, FileTransferStatus.FAILED
        )
        funcs = [call[0][0]["func"] for call in mock_nats_cmd.call_args_list]
        self.assertIn("files_download_prepare", funcs)
        self.assertIn("files_download_finalize", funcs)

    def test_init_file_download_session_limit_returns_429(self) -> None:
        """Fresh download init should honor the per-agent concurrency cap."""
        self._fill_agent_session_cap()
        response = self.client.post(
            self.url,
            {"source_path": r"C:\Users\Public\readme.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_init_file_download_user_session_limit_returns_429(self) -> None:
        """Per user cap applies across agents, not only the current one."""
        if FILE_TRANSFER_MAX_SESSIONS_PER_USER <= 0:
            self.skipTest("per-user transfer cap is disabled")
        self._fill_user_session_cap()
        response = self.client.post(
            self.url,
            {"source_path": r"C:\Users\Public\readme.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("this user", response.json())

    def test_init_file_download_invalid_session_id_returns_400(self) -> None:
        """Malformed resume session_id must be 400."""
        response = self.client.post(
            self.url,
            {"session_id": "not-a-uuid", "source_path": r"C:\Users\Public\readme.txt"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session_id", response.json())

    def test_init_file_download_non_string_source_returns_400(self) -> None:
        """Numeric source_path must not 500, path validation still rejects it."""
        response = self.client.post(self.url, {"source_path": 123}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("source_path", response.json())

    def test_init_file_download_long_filename_returns_400(self) -> None:
        """Derived basename over 255 chars must be 400, not a DataError 500."""
        leaf = ("a" * 256) + ".txt"
        response = self.client.post(
            self.url,
            {"source_path": rf"C:\Users\Public\{leaf}"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("too long", response.json())
        self.assertFalse(FileTransferSession.objects.filter(agent=self.agent).exists())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_file_download_max_filename_succeeds(self, mock_nats_cmd) -> None:
        """A 255-character basename is the column limit and must still init."""
        mock_nats_cmd.return_value = {"status": "ready", "total_size": 2048}
        leaf = "a" * 251 + ".txt"
        self.assertEqual(len(leaf), 255)
        response = self.client.post(
            self.url,
            {"source_path": rf"C:\Users\Public\{leaf}"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        session = FileTransferSession.objects.get(
            session_id=response.json()["session_id"]
        )
        self.assertEqual(session.filename, leaf)

    def test_init_file_download_invalid_resume_offset_returns_400(self) -> None:
        """Resume offset that is not an integer must be 400."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            destination_path=r"C:\Users\Public\readme.txt",
            filename="readme.txt",
        )
        response = self.client.post(
            self.url,
            {
                "session_id": str(session.session_id),
                "resume_offset": "halfway",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("resume_offset", response.json())

    @patch("agents.views.send_nats_command")
    def test_init_file_download_does_not_revive_failed_session(self, mock_send) -> None:
        """If the agent stream fails the row while prepare is in flight, init
        must not put it back to agent_ready with no stream behind it."""

        def prepare(agent, func, payload, timeout=60):
            FileTransferSession.objects.filter(session_id=payload["session_id"]).update(
                status=FileTransferStatus.FAILED, error_message="stream died"
            )
            return {"status": "ready", "total_size": 2048}

        mock_send.side_effect = prepare
        response = self.client.post(
            self.url, {"source_path": r"C:\Users\Public\readme.txt"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "stream died")
        session = FileTransferSession.objects.get(user=self.john)
        self.assertEqual(session.status, FileTransferStatus.FAILED)


class TestInitFileDownloadArchive(BaseFileBrowserAPITest):
    api_name = "init_file_download_archive"

    def test_init_archive_missing_paths(self) -> None:
        """Archive init requires at least one path."""
        response = self.client.post(self.url, {"paths": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paths", response.json())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_archive_success_returns_202(self, mock_nats_cmd) -> None:
        """Async prepare should return 202 while the agent builds the ZIP."""
        mock_nats_cmd.return_value = {"status": "building"}

        response = self.client.post(
            self.url,
            {
                "paths": [r"C:\Users\Public\Docs", r"C:\Users\Public\readme.txt"],
                "filename": "bundle",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        body = response.json()
        self.assertTrue(body["preparing"])
        self.assertTrue(body["is_archive"])
        self.assertEqual(body["filename"], "bundle.zip")
        self.assertEqual(body["status"], FileTransferStatus.WAITING_FOR_AGENT)
        self.assertEqual(body["total_size"], 0)

        session = FileTransferSession.objects.get(session_id=body["session_id"])
        self.assertTrue(session.is_archive)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["func"],
            "files_download_archive_prepare",
        )
        log = AuditLog.objects.get(action=AuditActionType.FILE_TRANSFER)
        self.assertEqual(log.after_value["operation"], "archive_download")
        self.assertEqual(len(log.after_value["paths"]), 2)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_archive_allows_apostrophe_in_paths(self, mock_nats_cmd) -> None:
        """ZIP download must accept the same names listing/mkdir already allow."""
        mock_nats_cmd.return_value = {"status": "building"}
        response = self.client.post(
            self.url,
            {"paths": [r"C:\Users\John's Docs", r"C:\Users\Public\a;b.txt"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_archive_agent_error(self, mock_nats_cmd) -> None:
        """Immediate validation failures from the agent should fail the session."""
        mock_nats_cmd.return_value = {"error": "too many files"}
        response = self.client.post(
            self.url,
            {"paths": [r"C:\Users\Public\Docs"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("too many files", response.json())
        self.assertEqual(
            FileTransferSession.objects.get().status, FileTransferStatus.FAILED
        )

    def test_init_archive_non_string_filename_does_not_500(self) -> None:
        """Json numbers in filename must not attribute error on .strip()."""
        with patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock) as mock_nats:
            mock_nats.return_value = {"status": "building"}
            response = self.client.post(
                self.url,
                {"paths": [r"C:\Users\Public\Docs"], "filename": 123},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.json()["filename"], "123.zip")

    def test_init_archive_paths_not_a_list_returns_400(self) -> None:
        """A string in paths must be 400."""
        response = self.client.post(
            self.url, {"paths": r"C:\Users\Public\Docs"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("paths", response.json())


class TestCancelFileDownload(BaseFileBrowserAPITest):
    @patch("agents.views.clear_download_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_download_success(self, mock_nats_cmd, _mock_clear) -> None:
        """Cancel should finalize on the agent and mark the session cancelled."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            destination_path=r"C:\Users\Public\readme.txt",
            filename="readme.txt",
        )
        mock_nats_cmd.return_value = {"status": "completed", "sha256": "abc"}

        url = self._session_url("cancel_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["func"], "files_download_finalize"
        )
        # Release, not completion: the agent must not hash the source.
        self.assertEqual(mock_nats_cmd.call_args[0][0]["payload"]["release"], "true")

    @patch("agents.views.clear_download_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_download_reason_error(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """reason=error should mark FAILED (auto-release after client failure)."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.AGENT_READY,
            destination_path=r"C:\Users\Public\readme.txt",
            filename="readme.txt",
        )
        mock_nats_cmd.return_value = {"status": "completed"}

        url = self._session_url("cancel_file_download", session.session_id)
        response = self.client.post(url, {"reason": "error"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.FAILED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)
        self.assertIn("failure", session.error_message.lower())

    @patch("agents.views.clear_download_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_download_failed_still_finalizes(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Failed downloads must still tell the agent to close the file handle."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.FAILED,
            destination_path=r"C:\Users\Public\readme.txt",
            filename="readme.txt",
            error_message="Download failed",
        )
        mock_nats_cmd.return_value = {"status": "completed"}
        url = self._session_url("cancel_file_download", session.session_id)
        response = self.client.post(url, {"reason": "error"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.FAILED)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["func"], "files_download_finalize"
        )

    @patch("agents.views.clear_download_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_file_download_skips_nats_when_agent_offline(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Offline cancel must still free the slot without waiting on nats."""
        self.agent.last_seen = djangotime.now() - dt.timedelta(minutes=10)
        self.agent.save(update_fields=["last_seen"])
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            destination_path=r"C:\Users\Public\readme.txt",
            filename="readme.txt",
        )
        url = self._session_url("cancel_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        mock_nats_cmd.assert_not_called()

    def test_cancel_other_users_download_is_not_found(self) -> None:
        """Cancel stays owner scoped; another user's download is not visible."""
        session = self._make_transfer_session(
            user=self.alice,
            operation=FileTransferOperation.DOWNLOAD,
            destination_path=r"C:\Users\Public\alice.txt",
            filename="alice.txt",
        )
        url = self._session_url("cancel_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)


class TestGetFileDownloadStatus(BaseFileBrowserAPITest):
    def test_get_file_download_status_success(self) -> None:
        """Status poll should return session fields without contacting the agent."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            destination_path=r"C:\Users\Public\Docs",
            filename="Docs.zip",
            is_archive=True,
            total_size=0,
            warnings='["skipped symlink"]',
        )

        url = self._session_url("get_file_download_status", session.session_id)
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["session_id"], str(session.session_id))
        self.assertEqual(body["status"], FileTransferStatus.WAITING_FOR_AGENT)
        self.assertTrue(body["is_archive"])
        self.assertEqual(body["warnings"], ["skipped symlink"])
        self.assertEqual(body["filename"], "Docs.zip")

    @patch("agents.views.clear_download_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_get_file_download_status_marks_expired(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """Active sessions past expires_at should expire and release the agent."""
        mock_nats_cmd.return_value = {"status": "completed"}
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            destination_path=r"C:\Users\Public\Docs",
            filename="Docs.zip",
            is_archive=True,
            expires_at=djangotime.now() - dt.timedelta(minutes=1),
        )

        url = self._session_url("get_file_download_status", session.session_id)
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.EXPIRED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.EXPIRED)
        self.assertEqual(session.error_message, "Session expired")
        mock_nats_cmd.assert_called_once()
        self.assertEqual(
            mock_nats_cmd.call_args[0][0]["func"], "files_download_finalize"
        )

    def test_get_file_download_status_other_user_is_not_found(self) -> None:
        """Status stays owner scoped."""
        session = self._make_transfer_session(
            user=self.alice,
            operation=FileTransferOperation.DOWNLOAD,
            destination_path=r"C:\Users\Public\alice.txt",
            filename="alice.txt",
        )
        url = self._session_url("get_file_download_status", session.session_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 404)


class TestListFileTransfers(BaseFileBrowserAPITest):
    api_name = "list_file_transfers"

    @patch("agents.views.get_download_ack", return_value=None)
    @patch("agents.views.get_upload_ack", return_value=750)
    def test_list_file_transfers_success(
        self, _mock_upload_ack, _mock_download_ack
    ) -> None:
        """Should list resumable sessions for the current user/agent only."""
        upload = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=500,
            filename="up.txt",
            destination_path=r"C:\Users\Public\up.txt",
        )
        download = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.AGENT_READY,
            filename="down.txt",
            destination_path=r"C:\Users\Public\down.txt",
            total_size=4096,
            committed_offset=0,
        )
        self._make_transfer_session(
            status=FileTransferStatus.COMPLETED,
            filename="done.txt",
            destination_path=r"C:\Users\Public\done.txt",
        )
        self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            filename="expired.txt",
            destination_path=r"C:\Users\Public\expired.txt",
            expires_at=djangotime.now() - dt.timedelta(minutes=5),
        )
        self._make_transfer_session(
            user=self.alice,
            status=FileTransferStatus.TRANSFERRING,
            filename="alice.txt",
            destination_path=r"C:\Users\Public\alice.txt",
        )

        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        transfers = response.json()["transfers"]
        self.assertEqual(len(transfers), 2)

        by_id = {item["session_id"]: item for item in transfers}
        self.assertIn(str(upload.session_id), by_id)
        self.assertIn(str(download.session_id), by_id)
        self.assertEqual(by_id[str(upload.session_id)]["committed_offset"], 750)
        self.assertEqual(
            by_id[str(upload.session_id)]["conflict_policy"],
            FileTransferConflictPolicy.REPLACE,
        )
        self.assertEqual(by_id[str(download.session_id)]["operation"], "download")
        self.assertNotIn("conflict_policy", by_id[str(download.session_id)])

        self.check_not_authenticated("get", self.url)


class TestUploadFileChunk(BaseFileBrowserAPITest):
    def _chunk_url(self, session_id):
        return self._session_url("upload_file_chunk", session_id)

    @patch("agents.views.get_accepted_offset", return_value=512)
    @patch("agents.views.get_upload_ack", return_value=512)
    def test_upload_chunk_replay_already_accepted_is_idempotent(
        self, _ack, _accepted
    ) -> None:
        """A retried put for an already accepted chunk must not fail the session."""
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=512,
            total_size=1024,
            chunk_size=512,
        )
        response = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * 512,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE="bytes 0-511/1024",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted_offset"], 512)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.get_accepted_offset", return_value=1024)
    @patch("agents.views.get_upload_ack", return_value=512)
    def test_upload_failed_by_agent_reports_the_reason(self, _ack, _accepted) -> None:
        session = self._make_transfer_session(
            status=FileTransferStatus.FAILED,
            error_message="insufficient disk space to upload file",
            committed_offset=512,
            total_size=2048,
            chunk_size=512,
        )
        ready = self.client.get(self._chunk_url(session.session_id))
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], FileTransferStatus.FAILED)
        self.assertEqual(
            ready.json()["error"], "insufficient disk space to upload file"
        )

        put = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * 512,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE="bytes 1024-1535/2048",
        )
        self.assertEqual(put.status_code, 400)
        self.assertEqual(put.json(), "insufficient disk space to upload file")

    @patch("agents.views.send_nats_notification", return_value=None)
    @patch("agents.views.store_upload_chunk", return_value=None)
    @patch("agents.views.get_accepted_offset")
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_upload_chunk_put_reports_room_for_next_chunk(
        self, _ack, mock_accepted, _store, _notify
    ) -> None:
        """The PUT says whether the next chunk fits, so the client can skip
        the ready GET while the pipeline has room."""
        chunk = 512
        total = (FILE_TRANSFER_PIPELINE_DEPTH + 2) * chunk
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            total_size=total,
            chunk_size=chunk,
        )

        def put(start):
            return self.client.put(
                self._chunk_url(session.session_id),
                data=b"x" * chunk,
                content_type="application/octet-stream",
                HTTP_CONTENT_RANGE=f"bytes {start}-{start + chunk - 1}/{total}",
            )

        # Before storing, accepted == start; after, the next chunk still fits.
        mock_accepted.side_effect = [0, chunk]
        response = put(0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["can_put"])

        # The chunk that fills the pipeline reports no room for the next one.
        last = (FILE_TRANSFER_PIPELINE_DEPTH - 1) * chunk
        mock_accepted.side_effect = [last, last + chunk]
        response = put(last)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["can_put"])

    def test_pipeline_depth_full_matches_download_cap(self) -> None:
        """Upload and download must reject at depth, not depth+1."""
        from agents.file_transfer_relay import pipeline_depth_full

        chunk = 512
        depth_bytes = FILE_TRANSFER_PIPELINE_DEPTH * chunk
        last_ok = (FILE_TRANSFER_PIPELINE_DEPTH - 1) * chunk
        self.assertFalse(pipeline_depth_full(0, 0, depth_bytes))
        self.assertFalse(pipeline_depth_full(last_ok, 0, depth_bytes))
        self.assertTrue(
            pipeline_depth_full(FILE_TRANSFER_PIPELINE_DEPTH * chunk, 0, depth_bytes)
        )
        self.assertTrue(
            pipeline_depth_full(
                (FILE_TRANSFER_PIPELINE_DEPTH + 1) * chunk, 0, depth_bytes
            )
        )
        self.assertFalse(
            pipeline_depth_full(
                FILE_TRANSFER_PIPELINE_DEPTH * chunk, chunk, depth_bytes
            )
        )

    @patch("agents.views.get_accepted_offset")
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_upload_chunk_depth_timeout_does_not_fail_session(
        self, _ack, mock_accepted
    ) -> None:
        """Depth wait timeout is retryable, the session stays transferring."""
        chunk = FILE_TRANSFER_CHUNK_SIZE
        start = FILE_TRANSFER_PIPELINE_DEPTH * chunk
        total = start + chunk
        mock_accepted.return_value = start
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=total,
            chunk_size=chunk,
        )
        response = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * chunk,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE=f"bytes {start}-{start + chunk - 1}/{total}",
        )
        self.assertEqual(response.status_code, 408)
        self.assertIn(
            "Timed out waiting for agent to commit previous chunk",
            response.json(),
        )
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.store_upload_chunk", return_value=None)
    @patch("agents.views.send_nats_notification", return_value=None)
    @patch("agents.views.get_accepted_offset")
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_upload_chunk_last_pipeline_slot_is_accepted(
        self, _ack, mock_accepted, _notify, _store
    ) -> None:
        """The depth-th in-flight chunk must still be accepted, matching download."""
        chunk = 512
        start = (FILE_TRANSFER_PIPELINE_DEPTH - 1) * chunk
        total = start + chunk
        mock_accepted.return_value = start
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=total,
            chunk_size=chunk,
        )
        response = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * chunk,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE=f"bytes {start}-{start + chunk - 1}/{total}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted_offset"], start + chunk)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.send_nats_notification", return_value=None)
    @patch("agents.views.get_accepted_offset", return_value=0)
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_cancel_during_first_chunk_is_not_overwritten(
        self, _ack, _accepted, mock_notify, mock_clear
    ) -> None:
        """The first chunk PUT used to overwrite a cancel with transferring."""
        session = self._make_transfer_session(
            status=FileTransferStatus.AGENT_READY,
            committed_offset=0,
            total_size=1024,
            chunk_size=512,
        )

        def cancel_meanwhile(*_args, **_kwargs):
            FileTransferSession.objects.filter(pk=session.pk).update(
                status=FileTransferStatus.CANCELLED
            )
            return None

        with patch("agents.views.store_upload_chunk", side_effect=cancel_meanwhile):
            response = self.client.put(
                self._chunk_url(session.session_id),
                data=b"x" * 512,
                content_type="application/octet-stream",
                HTTP_CONTENT_RANGE="bytes 0-511/1024",
            )
        self.assertEqual(response.status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        mock_clear.assert_called_once_with(session.session_id)
        mock_notify.assert_not_called()

    @patch("agents.views.rollback_upload_chunk")
    @patch("agents.views.store_upload_chunk", return_value=None)
    @patch("agents.views.get_accepted_offset", return_value=0)
    @patch("agents.views.get_upload_ack", return_value=0)
    @patch("agents.views.send_nats_notification")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_upload_chunk_natsdown_rolls_back_chunk(
        self, mock_nats_cmd, mock_notify, _ack, _accepted, _store, mock_rollback
    ) -> None:
        """Chunk is rolled back and the client retries, the session isn't failed."""
        mock_nats_cmd.return_value = {"status": "aborted"}
        mock_notify.return_value = notify_error("Unable to contact the agent")
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
            chunk_size=512,
        )
        response = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * 512,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE="bytes 0-511/1024",
        )
        self.assertEqual(response.status_code, 408)
        self.assertIn("Unable to contact the agent", response.json())
        self.assertNotIn("timed out waiting for agent to", response.json().lower())
        mock_rollback.assert_called_once()
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)
        mock_nats_cmd.assert_not_called()

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_upload_chunk_expired_aborts_agent(
        self, mock_nats_cmd, _mock_clear
    ) -> None:
        """TTL expiry on a chunk PUT must abort the agent session."""
        mock_nats_cmd.return_value = {"status": "aborted"}
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
            chunk_size=512,
            expires_at=djangotime.now() - dt.timedelta(minutes=1),
        )
        response = self.client.put(
            self._chunk_url(session.session_id),
            data=b"x" * 512,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE="bytes 0-511/1024",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.json())
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.EXPIRED)
        mock_nats_cmd.assert_called_once()
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_upload_abort")

    @patch("agents.views.get_accepted_offset")
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_upload_chunk_ready_get_reports_can_put(self, _ack, mock_accepted) -> None:
        """Bodyless get must report pipeline room without consuming a chunk body."""
        chunk = FILE_TRANSFER_CHUNK_SIZE
        total = (FILE_TRANSFER_PIPELINE_DEPTH + 1) * chunk
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=total,
            chunk_size=chunk,
        )
        url = self._chunk_url(session.session_id)

        mock_accepted.return_value = 0
        open_resp = self.client.get(url)
        self.assertEqual(open_resp.status_code, 200)
        self.assertTrue(open_resp.json()["can_put"])
        self.assertEqual(open_resp.json()["accepted_offset"], 0)
        self.assertEqual(open_resp.json()["committed_offset"], 0)

        mock_accepted.return_value = FILE_TRANSFER_PIPELINE_DEPTH * chunk
        full_resp = self.client.get(url)
        self.assertEqual(full_resp.status_code, 200)
        self.assertFalse(full_resp.json()["can_put"])
        self.assertEqual(
            full_resp.json()["accepted_offset"],
            FILE_TRANSFER_PIPELINE_DEPTH * chunk,
        )
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.get_accepted_offset", return_value=0)
    @patch("agents.views.get_upload_ack", return_value=0)
    def test_upload_chunk_ready_get_terminal_does_not_fail_session(
        self, _ack, _accepted
    ) -> None:
        """A failed session get reports can_put=false without changing status."""
        session = self._make_transfer_session(
            status=FileTransferStatus.FAILED,
            error_message="Upload failed",
        )
        response = self.client.get(self._chunk_url(session.session_id))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["can_put"])
        self.assertEqual(response.json()["status"], FileTransferStatus.FAILED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)


class TestCompleteFileUpload(BaseFileBrowserAPITest):
    def test_complete_upload_already_completed_is_idempotent(self) -> None:
        """A retried complete after success must not 400."""
        session = self._make_transfer_session(
            status=FileTransferStatus.COMPLETED,
            committed_offset=1024,
            total_size=1024,
        )
        url = self._session_url("complete_file_upload", session.session_id)
        response = self.client.post(url, {"sha256": "abc"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)
        self.assertEqual(response.json()["sha256"], "abc")

    @patch("agents.views.get_upload_ack", return_value=0)
    def test_complete_upload_timeout_does_not_fail_session(self, _ack) -> None:
        """Final chunk wait timeout is retryable, the session stays transferring."""
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
        )
        url = self._session_url("complete_file_upload", session.session_id)
        response = self.client.post(url, {"sha256": "abc"}, format="json")
        self.assertEqual(response.status_code, 408)
        self.assertIn(
            "Timed out waiting for agent to commit final chunk",
            response.json(),
        )
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.get_upload_ack", return_value=1024)
    @patch("agents.views.send_nats_command")
    def test_complete_upload_nats_error_does_not_overwrite_completed(
        self, mock_nats, _ack, _clear
    ) -> None:
        """A losing complete must not flip a peer completed session to failed."""
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=1024,
            total_size=1024,
        )

        def nats_side_effect(agent, func, payload, timeout=30, **kwargs):
            FileTransferSession.objects.filter(pk=session.pk).update(
                status=FileTransferStatus.COMPLETED,
                error_message="",
            )
            return notify_error(
                f"{func.replace('_', ' ').title()} failed: upload session not found"
            )

        mock_nats.side_effect = nats_side_effect
        url = self._session_url("complete_file_upload", session.session_id)
        response = self.client.post(url, {"sha256": "abc"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)
        self.assertEqual(mock_nats.call_args[0][1], "files_upload_finalize")

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.get_upload_ack", return_value=1024)
    @patch("agents.views.send_nats_command")
    def test_complete_upload_completed_during_fail_still_succeeds(
        self, mock_nats, _ack, _clear
    ) -> None:
        """If a peer completes while we are failing, keep completed and 200."""
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=1024,
            total_size=1024,
        )

        def nats_side_effect(agent, func, payload, timeout=30, **kwargs):
            if func == "files_upload_finalize":
                return notify_error(
                    "Files Upload Finalize failed: upload session not found"
                )
            FileTransferSession.objects.filter(pk=session.pk).update(
                status=FileTransferStatus.COMPLETED,
                error_message="",
            )
            return {"status": "aborted"}

        mock_nats.side_effect = nats_side_effect
        url = self._session_url("complete_file_upload", session.session_id)
        response = self.client.post(url, {"sha256": "abc"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)
        funcs = [call[0][1] for call in mock_nats.call_args_list]
        self.assertIn("files_upload_finalize", funcs)
        self.assertIn("files_upload_abort", funcs)

    @patch("agents.views.clear_upload_session_redis")
    @patch("agents.views.get_upload_ack", return_value=1024)
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_complete_upload_real_nats_error_fails_session(
        self, mock_nats_cmd, _ack, _clear
    ) -> None:
        """A genuine finalize failure still marks the session failed."""
        mock_nats_cmd.return_value = {"error": "disk full"}
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=1024,
            total_size=1024,
        )
        url = self._session_url("complete_file_upload", session.session_id)
        response = self.client.post(url, {"sha256": "abc"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("disk full", response.json())
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)
        funcs = [call[0][0]["func"] for call in mock_nats_cmd.call_args_list]
        self.assertIn("files_upload_finalize", funcs)
        self.assertIn("files_upload_abort", funcs)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_fail_transfer_session_does_not_overwrite_completed(
        self, mock_nats_cmd
    ) -> None:
        from agents.views import _fail_transfer_session

        mock_nats_cmd.return_value = {"status": "aborted"}
        session = self._make_transfer_session(status=FileTransferStatus.COMPLETED)
        _fail_transfer_session(session, self.agent, "upload session not found")
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)
        mock_nats_cmd.assert_not_called()

    def test_mark_transfer_completed_overwrites_failed_not_cancelled(self) -> None:
        from agents.views import _mark_transfer_completed

        failed = self._make_transfer_session(status=FileTransferStatus.FAILED)
        self.assertEqual(
            _mark_transfer_completed(failed).status, FileTransferStatus.COMPLETED
        )

        cancelled = self._make_transfer_session(
            status=FileTransferStatus.CANCELLED,
            filename="cancelled.txt",
            destination_path=r"C:\Users\Public\cancelled.txt",
        )
        self.assertEqual(
            _mark_transfer_completed(cancelled).status, FileTransferStatus.CANCELLED
        )


class TestGetFileDownloadChunk(BaseFileBrowserAPITest):
    def _chunk_url(self, session_id):
        return self._session_url("get_file_download_chunk", session_id)

    @patch("agents.views.get_download_offered_offset", return_value=None)
    @patch("agents.views.get_download_ack", return_value=0)
    def test_download_chunk_not_ready_does_not_fail_session(
        self, _ack, _offered
    ) -> None:
        """No chunk yet is 204 (poll again), not an error status, and must not
        pin or fail the session."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
        )
        response = self.client.get(self._chunk_url(session.session_id))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)


class TestCompleteFileDownload(BaseFileBrowserAPITest):
    def test_complete_download_already_completed_is_idempotent(self) -> None:
        """A retried download complete after success must not 400."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.COMPLETED,
            committed_offset=1024,
            total_size=1024,
        )
        url = self._session_url("complete_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)

    @patch("agents.views.get_download_ack", return_value=0)
    def test_complete_download_timeout_does_not_fail_session(self, _ack) -> None:
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
        )
        url = self._session_url("complete_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 408)
        self.assertIn("Timed out waiting for client to ACK all chunks", response.json())
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_complete_unreachable_agent_is_retryable(self, mock_nats_cmd) -> None:
        """A finalize that cannot reach the agent must not fail a transfer
        whose bytes are all committed; the client retries the complete."""
        mock_nats_cmd.return_value = "timeout"
        for operation, api_name, ack in (
            (FileTransferOperation.UPLOAD, "complete_file_upload", "get_upload_ack"),
            (
                FileTransferOperation.DOWNLOAD,
                "complete_file_download",
                "get_download_ack",
            ),
        ):
            with self.subTest(operation=operation), patch(
                f"agents.views.{ack}", return_value=1024
            ):
                session = self._make_transfer_session(
                    operation=operation,
                    status=FileTransferStatus.TRANSFERRING,
                    committed_offset=1024,
                    total_size=1024,
                )
                url = self._session_url(api_name, session.session_id)
                response = self.client.post(url, {}, format="json")
                self.assertEqual(response.status_code, 408)
                self.assertIn(
                    "Timed out waiting for agent to finalize", response.json()
                )
                session.refresh_from_db()
                self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("agents.views.clear_download_session_redis")
    @patch("agents.views.get_download_ack", return_value=1024)
    @patch("agents.views.send_nats_command")
    def test_complete_download_nats_error_does_not_overwrite_completed(
        self, mock_nats, _ack, _clear
    ) -> None:
        """A losing download complete must keep the peer completed status."""
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=1024,
            total_size=1024,
        )

        def nats_side_effect(agent, func, payload, timeout=30, **kwargs):
            FileTransferSession.objects.filter(pk=session.pk).update(
                status=FileTransferStatus.COMPLETED,
                error_message="",
            )
            return notify_error(
                f"{func.replace('_', ' ').title()} failed: download session not found"
            )

        mock_nats.side_effect = nats_side_effect
        url = self._session_url("complete_file_download", session.session_id)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], FileTransferStatus.COMPLETED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)
        self.assertEqual(mock_nats.call_args[0][1], "files_download_finalize")


class TestAgentDownloadPutChunk(BaseFileBrowserAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate_agent(self.agent)

    @patch("apiv3.file_transfer_views.get_download_offered_offset")
    @patch("apiv3.file_transfer_views.get_download_ack", return_value=0)
    def test_depth_not_ready_does_not_fail_session(self, _ack, mock_offered) -> None:
        """Agent depth check must 408 without failing the session or blocking a worker."""
        chunk = FILE_TRANSFER_CHUNK_SIZE
        start = FILE_TRANSFER_PIPELINE_DEPTH * chunk
        total = start + chunk
        mock_offered.return_value = start
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=total,
            chunk_size=chunk,
        )
        url = reverse("file_transfer_download_put_chunk", args=[session.session_id])
        response = self.client.put(
            url,
            data=b"x" * chunk,
            content_type="application/octet-stream",
            HTTP_CONTENT_RANGE=f"bytes {start}-{start + chunk - 1}/{total}",
        )
        self.assertEqual(response.status_code, 408)
        self.assertIn(
            "Timed out waiting for client to ACK previous chunk",
            response.json(),
        )
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    @patch("apiv3.file_transfer_views.get_download_offered_offset")
    @patch("apiv3.file_transfer_views.get_download_ack", return_value=0)
    def test_download_chunk_ready_get_reports_can_put(self, _ack, mock_offered) -> None:
        chunk = FILE_TRANSFER_CHUNK_SIZE
        total = (FILE_TRANSFER_PIPELINE_DEPTH + 1) * chunk
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=total,
            chunk_size=chunk,
        )
        url = reverse("file_transfer_download_put_chunk", args=[session.session_id])

        mock_offered.return_value = 0
        open_resp = self.client.get(url)
        self.assertEqual(open_resp.status_code, 200)
        self.assertTrue(open_resp.json()["can_put"])
        self.assertEqual(open_resp.json()["offered_offset"], 0)
        self.assertEqual(open_resp.json()["committed_offset"], 0)

        mock_offered.return_value = FILE_TRANSFER_PIPELINE_DEPTH * chunk
        full_resp = self.client.get(url)
        self.assertEqual(full_resp.status_code, 200)
        self.assertFalse(full_resp.json()["can_put"])
        self.assertEqual(
            full_resp.json()["offered_offset"],
            FILE_TRANSFER_PIPELINE_DEPTH * chunk,
        )


class TestAgentDownloadPutCancelRace(BaseFileBrowserAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate_agent(self.agent)

    @patch("apiv3.file_transfer_views.clear_download_session_redis")
    @patch("apiv3.file_transfer_views.get_download_offered_offset", return_value=0)
    @patch("apiv3.file_transfer_views.get_download_ack", return_value=0)
    def test_cancel_during_first_push_is_not_overwritten(
        self, _ack, _offered, mock_clear
    ) -> None:
        chunk = FILE_TRANSFER_CHUNK_SIZE
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.AGENT_READY,
            committed_offset=0,
            total_size=2 * chunk,
            chunk_size=chunk,
        )

        def cancel_meanwhile(*_args, **_kwargs):
            FileTransferSession.objects.filter(pk=session.pk).update(
                status=FileTransferStatus.CANCELLED
            )
            return None

        url = reverse("file_transfer_download_put_chunk", args=[session.session_id])
        with patch(
            "apiv3.file_transfer_views.store_download_chunk",
            side_effect=cancel_meanwhile,
        ):
            response = self.client.put(
                url,
                data=b"x" * chunk,
                content_type="application/octet-stream",
                HTTP_CONTENT_RANGE=f"bytes 0-{chunk - 1}/{2 * chunk}",
            )
        self.assertEqual(response.status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        mock_clear.assert_called_once_with(session.session_id)


class TestWindowsReservedNames(TacticalTestCase):
    def test_reserved_device_names(self) -> None:
        from agents.utils import (
            validate_file_browser_name,
            validate_file_transfer_filename,
        )

        for name in ("CON", "nul.txt", "com1.log", "Lpt9", "aux.tar.gz"):
            self.assertIn(
                "reserved by Windows",
                validate_file_browser_name(name, plat=AgentPlat.WINDOWS) or "",
                name,
            )
            self.assertIn(
                "reserved by Windows",
                validate_file_transfer_filename(name, ban_windows_reserved=True) or "",
            )
            self.assertIsNone(validate_file_browser_name(name, plat=AgentPlat.LINUX))
        for name in ("console.txt", "nullable", "COM10", "lpt.txt"):
            self.assertIsNone(validate_file_browser_name(name, plat=AgentPlat.WINDOWS))
        self.assertIsNone(validate_file_transfer_filename("con.zip"))


class TestUploadSameDestination(BaseFileBrowserAPITest):
    api_name = "init_file_upload"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_second_upload_to_same_file_is_refused(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "ready", "committed_offset": 0}
        self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            destination_path=r"C:\Users\Public\Report.txt",
            filename="Report.txt",
        )
        body = {
            "filename": "report.txt",
            "destination_path": r"C:\Users\Public",
            "total_size": 10,
        }
        response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Another upload to this file", response.json())
        mock_nats_cmd.assert_not_called()

        body["filename"] = "other.txt"
        response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 200)


class TestResumeCancelRace(BaseFileBrowserAPITest):
    def _cancel_during(self, session, prepare_func):
        calls = []

        def nats(agent, func, payload, *args, **kwargs):
            calls.append(func)
            if func == prepare_func:
                FileTransferSession.objects.filter(pk=session.pk).update(
                    status=FileTransferStatus.CANCELLED
                )
                return {"status": "ready", "committed_offset": 512, "total_size": 1024}
            return {"status": "ok"}

        return calls, nats

    @patch("agents.views.clear_upload_session_redis")
    def test_upload_resume(self, _clear) -> None:
        session = self._make_transfer_session(committed_offset=512)
        calls, nats = self._cancel_during(session, "files_upload_prepare")
        with patch("agents.views.send_nats_command", side_effect=nats):
            response = self.client.post(
                reverse("init_file_upload", args=[self.agent.agent_id]),
                {"session_id": str(session.session_id)},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        self.assertEqual(calls, ["files_upload_prepare", "files_upload_abort"])

    @patch("agents.views.clear_download_session_redis")
    def test_download_resume(self, _clear) -> None:
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            destination_path=r"C:\Users\Public\demo.txt",
            committed_offset=0,
        )
        calls, nats = self._cancel_during(session, "files_download_prepare")
        with patch("agents.views.send_nats_command", side_effect=nats):
            response = self.client.post(
                reverse("init_file_download", args=[self.agent.agent_id]),
                {"session_id": str(session.session_id), "resume_offset": 0},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)
        self.assertEqual(calls, ["files_download_prepare", "files_download_finalize"])


class TestArchiveReadyAfterCancel(BaseFileBrowserAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate_agent(self.agent)

    def test_ready_after_cancel_is_refused(self) -> None:
        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            is_archive=True,
        )
        FileTransferSession.objects.filter(pk=session.pk).update(
            status=FileTransferStatus.CANCELLED
        )
        # view still has the row from before the cancel
        with patch("apiv3.file_transfer_views.get_object_or_404", return_value=session):
            response = self.client.post(
                reverse("file_transfer_archive_ready", args=[session.session_id]),
                {"total_size": 10, "archive_path": "/tmp/trmm-archive-x.zip"},
                format="json",
            )
        self.assertEqual(response.status_code, 409)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.CANCELLED)


class TestAgentUploadPull(BaseFileBrowserAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate_agent(self.agent)

    @patch("apiv3.file_transfer_views.peek_upload_chunk")
    @patch("apiv3.file_transfer_views.get_upload_ack", return_value=0)
    def test_next_chunk_is_not_consumed_by_the_pull(self, _ack, mock_peek) -> None:
        from agents.file_transfer_relay import PendingUploadChunk

        mock_peek.return_value = PendingUploadChunk(start=0, end=511, data=b"x" * 512)
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
            chunk_size=512,
        )
        url = reverse("file_transfer_next_chunk", args=[session.session_id])
        for _ in range(2):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["X-Chunk-Start"], "0")
        self.assertEqual(mock_peek.call_count, 2)

    @patch("apiv3.file_transfer_views.signal_upload_ack")
    @patch("apiv3.file_transfer_views.delete_upload_chunk")
    @patch("apiv3.file_transfer_views.get_accepted_offset", return_value=1024)
    @patch("apiv3.file_transfer_views.get_upload_ack")
    def test_ack_deletes_the_acked_chunk_once(
        self, mock_ack, _accepted, mock_delete, _signal
    ) -> None:
        session = self._make_transfer_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=0,
            total_size=1024,
            chunk_size=512,
        )
        url = reverse("file_transfer_ack", args=[session.session_id])

        mock_ack.return_value = 0
        response = self.client.post(url, {"committed_offset": 512}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once_with(session.session_id, 0)

        # re-ack after a lost response
        mock_ack.return_value = 512
        response = self.client.post(url, {"committed_offset": 512}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once()


class TestFileBrowserPermissions(BaseFileBrowserAPITest):
    def test_new_role_file_browser_defaults_false(self) -> None:
        role = baker.make("accounts.Role")
        self.assertFalse(role.can_use_file_browser)

    def test_mesh_permission_does_not_grant_file_browser(self) -> None:
        defaults_url = reverse("file_browser_defaults", args=[self.agent.agent_id])
        list_url = reverse("list_files", args=[self.agent.agent_id])
        user = self.create_user_with_roles(["can_use_mesh"])
        self.client.force_authenticate(user=user)

        self.check_not_authorized("get", defaults_url)
        self.check_not_authorized("get", list_url)

    def test_file_browser_permission_allows_defaults(self) -> None:
        url = reverse("file_browser_defaults", args=[self.agent.agent_id])
        user = self.create_user_with_roles(["can_use_file_browser"])
        self.client.force_authenticate(user=user)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("file_browser_mode", response.json())
        self.assertTrue(response.json()["supports_new_file_browser"])

    def test_file_browser_defaults_old_agent_does_not_support_new(self) -> None:
        """Defaults stay 200 for old agents so the UI can fall back to Mesh."""
        self.agent.version = "2.10.0"
        self.agent.save(update_fields=["version"])
        url = reverse("file_browser_defaults", args=[self.agent.agent_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["supports_new_file_browser"])

    def test_file_browser_defaults_max_upload_file_size(self) -> None:
        url = reverse("file_browser_defaults", args=[self.agent.agent_id])
        response = self.client.get(url)
        self.assertEqual(response.json()["max_upload_file_size_bytes"], 0)

        with patch(
            "agents.serializers.FILE_BROWSER_MAX_UPLOAD_FILE_SIZE_BYTES", 2 * 2**30
        ):
            response = self.client.get(url)
        self.assertEqual(response.json()["max_upload_file_size_bytes"], 2 * 2**30)

    def test_copy_mesh_permission_to_file_browser(self) -> None:
        import importlib

        from django.apps import apps

        mesh = baker.make(
            "accounts.Role", can_use_mesh=True, can_use_file_browser=False
        )
        other = baker.make(
            "accounts.Role", can_use_mesh=False, can_use_file_browser=False
        )
        already = baker.make(
            "accounts.Role", can_use_mesh=True, can_use_file_browser=True
        )

        migration = importlib.import_module(
            "accounts.migrations.0044_copy_mesh_permission_to_file_browser"
        )
        migration.copy_can_use_mesh_to_file_browser(apps, None)

        mesh.refresh_from_db()
        other.refresh_from_db()
        already.refresh_from_db()
        self.assertTrue(mesh.can_use_file_browser)
        self.assertFalse(other.can_use_file_browser)
        self.assertTrue(already.can_use_file_browser)


class TestExpireStaleFileTransfers(BaseFileBrowserAPITest):
    def _age_session(self, session: FileTransferSession, minutes: int) -> None:
        then = djangotime.now() - dt.timedelta(minutes=minutes)
        FileTransferSession.objects.filter(pk=session.pk).update(
            created_at=then, updated_at=then
        )

    @patch("agents.file_transfer_relay.get_download_ack", return_value=None)
    def test_archive_ready_recently_is_not_idle_expired(self, _ack) -> None:
        """A build that took longer than the idle window still gets the full
        window after archive-ready updates the row."""
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.AGENT_READY,
            is_archive=True,
            committed_offset=0,
            filename="Docs.zip",
        )
        FileTransferSession.objects.filter(pk=session.pk).update(
            created_at=djangotime.now()
            - dt.timedelta(minutes=FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 5)
        )
        expire_stale_file_transfer_sessions(notify_agent=False)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.AGENT_READY)

    @patch("agents.file_transfer_relay.clear_download_session_redis")
    @patch("agents.file_transfer_relay.clear_upload_session_redis")
    @patch("agents.file_transfer_relay.get_upload_ack", return_value=None)
    @patch("agents.utils.send_nats_command")
    def test_init_sweep_releases_expired_sessions_after_commit(
        self, mock_send, *_mocks
    ) -> None:
        """Sessions expired by the init-time sweep must still be released on
        the agent, once the row locks are dropped."""
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(committed_offset=0)
        self._age_session(session, FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 1)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            expire_stale_file_transfer_sessions(agent=self.agent, notify_agent=False)
            mock_send.assert_not_called()
        self.assertEqual(len(callbacks), 1)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][1], "files_upload_abort")
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.EXPIRED)

    @patch("agents.file_transfer_relay.clear_download_session_redis")
    @patch("agents.file_transfer_relay.clear_upload_session_redis")
    @patch("agents.file_transfer_relay.get_download_ack", return_value=None)
    @patch("agents.file_transfer_relay.get_upload_ack", return_value=None)
    def test_idle_never_started_session_expires(self, *_mocks) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(committed_offset=0)
        self._age_session(session, FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 1)
        expire_stale_file_transfer_sessions(notify_agent=False)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.EXPIRED)
        self.assertIn("10 minutes", session.error_message)

    @patch("agents.file_transfer_relay.get_download_ack", return_value=None)
    @patch("agents.file_transfer_relay.get_upload_ack", return_value=None)
    def test_recent_never_started_session_stays_active(self, *_mocks) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(committed_offset=0)
        expire_stale_file_transfer_sessions(notify_agent=False)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    def test_progressed_session_is_not_idle_expired(self) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(committed_offset=512)
        self._age_session(session, FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 1)
        expire_stale_file_transfer_sessions(notify_agent=False)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    def test_archive_still_preparing_is_not_idle_expired(self) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        session = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            is_archive=True,
            committed_offset=0,
            filename="Docs.zip",
            destination_path=r"C:\Users\Public\Docs",
        )
        self._age_session(session, FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 1)
        expire_stale_file_transfer_sessions(notify_agent=False)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.WAITING_FOR_AGENT)

    @patch("agents.file_transfer_relay.clear_download_session_redis")
    @patch("agents.file_transfer_relay.clear_upload_session_redis")
    @patch("agents.file_transfer_relay.get_download_ack", return_value=None)
    @patch("agents.file_transfer_relay.get_upload_ack", return_value=None)
    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_idle_sessions_free_cap_on_next_init(self, mock_nats, *_acks) -> None:
        """Abandoned never started sessions must not block a new init after 10 minutes."""
        mock_nats.return_value = {"status": "ready", "committed_offset": 0}
        for i in range(FILE_TRANSFER_MAX_SESSIONS_PER_AGENT):
            session = self._make_transfer_session(
                filename=f"stale-{i}.txt",
                destination_path=rf"C:\Users\Public\stale-{i}.txt",
                committed_offset=0,
            )
            self._age_session(session, FILE_TRANSFER_IDLE_EXPIRE_MINUTES + 1)

        url = reverse("init_file_upload", args=[self.agent.agent_id])
        response = self.client.post(
            url,
            {
                "filename": "fresh.txt",
                "destination_path": r"C:\Users\Public",
                "total_size": 1024,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("agents.file_transfer_relay.clear_download_session_redis")
    @patch("agents.file_transfer_relay.clear_upload_session_redis")
    @patch("agents.utils.send_nats_command")
    def test_already_expired_without_error_notifies_agent(
        self, mock_nats, *_clears
    ) -> None:
        """Celery must still abort sessions that expired without an agent release."""
        from agents.tasks import expire_stale_file_transfer_sessions

        self.agent.last_seen = djangotime.now()
        self.agent.save(update_fields=["last_seen"])
        session = self._make_transfer_session(
            status=FileTransferStatus.EXPIRED,
            error_message="",
        )
        expire_stale_file_transfer_sessions(notify_agent=True)
        session.refresh_from_db()
        self.assertEqual(session.error_message, "Session expired")
        mock_nats.assert_called_once()
        self.assertEqual(mock_nats.call_args[0][1], "files_upload_abort")

    def test_cleanup_task_runs_every_ten_minutes(self) -> None:
        from celery.schedules import crontab

        from tacticalrmm.celery import app

        schedule = app.conf.beat_schedule["cleanup-expired-file-transfers"]["schedule"]
        self.assertEqual(schedule, crontab(minute="*/10"))


class TestMalformedFileBrowserBodies(BaseFileBrowserAPITest):
    """Wrong-typed fields and non-object bodies must be a 400, never a 500."""

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_user_endpoints_reject_wrong_types(self, mock_nats_cmd) -> None:
        agent_url = lambda name: reverse(name, args=[self.agent.agent_id])  # noqa: E731
        upload = self._make_transfer_session(
            operation=FileTransferOperation.UPLOAD, committed_offset=1024
        )
        download = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            filename="dl.txt",
            destination_path=r"C:\Users\Public\dl.txt",
        )
        cases = [
            (agent_url("check_file_exists"), {"path": 123, "names": ["a.txt"]}),
            (agent_url("check_file_exists"), ["not", "an", "object"]),
            (agent_url("create_file_folder"), {"path": 123, "name": "new"}),
            (agent_url("rename_file"), {"path": 123, "new_name": "b.txt"}),
            (
                self._session_url("complete_file_upload", upload.session_id),
                {"sha256": 123},
            ),
            (
                self._session_url("cancel_file_upload", upload.session_id),
                {"reason": 123},
            ),
            (
                self._session_url("cancel_file_download", download.session_id),
                {"reason": ["error"]},
            ),
            (
                self._session_url("ack_file_download_chunk", download.session_id),
                [1024],
            ),
        ]
        for url, body in cases:
            with self.subTest(url=url, body=body):
                response = self.client.post(url, body, format="json")
                self.assertEqual(response.status_code, 400, response.content)

        response = self.client.delete(
            agent_url("list_files"), ["C:\\Temp\\a.txt"], format="json"
        )
        self.assertEqual(response.status_code, 400)
        mock_nats_cmd.assert_not_called()

    @patch("apiv3.file_transfer_views.clear_download_session_redis")
    def test_agent_fail_accepts_non_string_error(self, _clear) -> None:
        self.authenticate_agent(self.agent)
        session = self._make_transfer_session(operation=FileTransferOperation.DOWNLOAD)
        url = reverse("file_transfer_fail", args=[session.session_id])

        response = self.client.post(url, {"error": 123}, format="json")

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)
        self.assertEqual(session.error_message, "123")


class TestTrailingPeriodNamesByPlatform(BaseFileBrowserAPITest):
    """Only Windows strips a trailing space or period, so only Windows
    agents reject such names."""

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_linux_accepts_trailing_period(self, mock_nats_cmd) -> None:
        self.agent.plat = "linux"
        self.agent.save(update_fields=["plat"])
        mock_nats_cmd.return_value = {
            "name": "notes.",
            "path": "/tmp/notes.",
            "type": "folder",
        }
        agent_url = lambda name: reverse(name, args=[self.agent.agent_id])  # noqa: E731

        response = self.client.post(
            agent_url("create_file_folder"),
            {"path": "/tmp", "name": "notes."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(mock_nats_cmd.call_args[0][0]["payload"]["name"], "notes.")

        mock_nats_cmd.return_value = {"status": "ready"}
        response = self.client.post(
            agent_url("init_file_upload"),
            {
                "filename": "notes.",
                "destination_path": "/tmp",
                "total_size": 10,
            },
            format="json",
        )
        self.assertNotIn("period", str(response.content))

    def test_windows_rejects_trailing_period(self) -> None:
        response = self.client.post(
            reverse("create_file_folder", args=[self.agent.agent_id]),
            {"path": r"C:\Temp", "name": "notes."},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("period", response.json())


class TestAgentFileTransferFail(BaseFileBrowserAPITest):
    @patch("apiv3.file_transfer_views.clear_upload_session_redis")
    def test_fail_does_not_overwrite_completed(self, _clear) -> None:
        self.authenticate_agent(self.agent)
        session = self._make_transfer_session(status=FileTransferStatus.COMPLETED)
        url = reverse("file_transfer_fail", args=[session.session_id])

        response = self.client.post(url, {"error": "late"}, format="json")

        self.assertEqual(response.status_code, 409)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)


class TestFileExtract(BaseFileBrowserAPITest):
    api_name = "init_file_extract"
    body = {
        "source_path": r"C:\Users\Public\Bundle.ZIP",
        "destination_path": r"C:\Users\Public\Bundle",
    }

    def _make_extract_session(self, **kwargs) -> FileTransferSession:
        defaults = {
            "operation": FileTransferOperation.EXTRACT,
            "status": FileTransferStatus.WAITING_FOR_AGENT,
            "source_path": self.body["source_path"],
            "destination_path": self.body["destination_path"],
            "filename": "Bundle.ZIP",
            "conflict_policy": FileTransferConflictPolicy.SKIP,
            "total_size": 0,
            "chunk_size": 0,
        }
        defaults.update(kwargs)
        return self._make_transfer_session(**defaults)

    def test_validation(self) -> None:
        for body, message in (
            ({**self.body, "source_path": r"C:\Users\Public\a.rar"}, "Only .zip"),
            ({**self.body, "source_path": "Bundle.zip"}, "The ZIP path must be"),
            ({**self.body, "destination_path": "rel\\dir"}, "The destination must"),
            ({**self.body, "destination_path": r"C:\a\..\b"}, "traversal"),
            ({**self.body, "conflict_policy": "merge"}, "conflict_policy"),
            ({"source_path": self.body["source_path"]}, "The destination is required"),
            ({**self.body, "destination_path": 5}, "must be a string"),
        ):
            response = self.client.post(self.url, body, format="json")
            self.assertEqual(response.status_code, 400, body)
            self.assertIn(message, response.json())
        self.assertFalse(FileTransferSession.objects.exists())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_init_success(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        session = FileTransferSession.objects.get(
            session_id=response.json()["session_id"]
        )
        self.assertEqual(session.operation, FileTransferOperation.EXTRACT)
        self.assertEqual(session.status, FileTransferStatus.WAITING_FOR_AGENT)
        self.assertEqual(session.filename, "Bundle.ZIP")
        self.assertEqual(session.conflict_policy, FileTransferConflictPolicy.SKIP)
        self.assertLessEqual(
            session.expires_at,
            djangotime.now() + dt.timedelta(minutes=FILE_TRANSFER_IDLE_EXPIRE_MINUTES),
        )
        sent = mock_nats_cmd.call_args[0][0]
        self.assertEqual(sent["func"], "files_extract_prepare")
        self.assertEqual(sent["payload"]["conflict_policy"], "skip")
        self.assertEqual(sent["payload"]["max_files"], "10000")
        self.assertEqual(sent["payload"]["max_size_bytes"], str(4 * 1024**3))
        self.assertEqual(sent["payload"]["max_depth"], "32")
        self.assertEqual(sent["payload"]["destination_path"], r"C:\Users\Public\Bundle")

        log = AuditLog.objects.get(action=AuditActionType.MODIFY)
        self.assertEqual(log.after_value["operation"], "extract")
        self.assertEqual(log.after_value["paths"], [self.body["source_path"]])
        self.assertEqual(log.after_value["destination"], self.body["destination_path"])
        self.assertEqual(log.after_value["conflict_policy"], "skip")

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_replace_policy_and_linux_paths(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        self.agent.plat = AgentPlat.LINUX
        self.agent.save(update_fields=["plat"])
        response = self.client.post(
            self.url,
            {
                "source_path": "/root/a.zip",
                "destination_path": "/root/out/",
                "conflict_policy": "Replace",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        payload = mock_nats_cmd.call_args[0][0]["payload"]
        self.assertEqual(payload["conflict_policy"], "replace")
        self.assertEqual(payload["destination_path"], "/root/out")

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_agent_error_fails_session(self, mock_nats_cmd) -> None:
        for reply in ({"error": "invalid destination_path"}, "timeout"):
            mock_nats_cmd.reset_mock()
            mock_nats_cmd.return_value = reply
            response = self.client.post(self.url, self.body, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(
            list(FileTransferSession.objects.values_list("status", flat=True)),
            [FileTransferStatus.FAILED] * 2,
        )
        self.assertFalse(
            AuditLog.objects.filter(action=AuditActionType.MODIFY).exists()
        )

    def test_slot_limit(self) -> None:
        self._fill_agent_session_cap()
        response = self.client.post(self.url, self.body, format="json")
        self.assertEqual(response.status_code, 429)

    def test_permissions(self) -> None:
        session = self._make_extract_session()
        user = self.create_user_with_roles(["can_use_mesh"])
        self.client.force_authenticate(user=user)
        self.check_not_authorized("post", self.url, self.body)
        self.check_not_authorized(
            "get", self._session_url("get_file_extract_status", session.session_id)
        )
        self.check_not_authorized(
            "post", self._session_url("cancel_file_extract", session.session_id)
        )

    def test_owner_only(self) -> None:
        session = self._make_extract_session()
        other = self.create_user_with_roles(["can_use_file_browser"])
        self.client.force_authenticate(user=other)
        response = self.client.get(
            self._session_url("get_file_extract_status", session.session_id)
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            self._session_url("cancel_file_extract", session.session_id)
        )
        self.assertEqual(response.status_code, 404)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.WAITING_FOR_AGENT)

    def test_status_and_listing(self) -> None:
        session = self._make_extract_session(
            status=FileTransferStatus.TRANSFERRING,
            total_size=1000,
            committed_offset=400,
            files_done=4,
            files_total=10,
        )
        response = self.client.get(
            self._session_url("get_file_extract_status", session.session_id)
        )
        body = response.json()
        self.assertEqual(body["status"], FileTransferStatus.TRANSFERRING)
        self.assertEqual((body["committed_offset"], body["total_size"]), (400, 1000))
        self.assertEqual((body["files_done"], body["files_total"]), (4, 10))
        self.assertEqual(body["source_path"], self.body["source_path"])

        listed = self.client.get(
            reverse("list_file_transfers", args=[self.agent.agent_id])
        ).json()["transfers"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["operation"], FileTransferOperation.EXTRACT)
        self.assertEqual(listed[0]["committed_offset"], 400)
        self.assertEqual(listed[0]["files_total"], 10)
        self.assertEqual(listed[0]["source_path"], self.body["source_path"])

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_status_expires_overdue_session(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "cancelled"}
        session = self._make_extract_session(
            expires_at=djangotime.now() - dt.timedelta(seconds=1)
        )
        body = self.client.get(
            self._session_url("get_file_extract_status", session.session_id)
        ).json()
        self.assertEqual(body["status"], FileTransferStatus.EXPIRED)
        self.assertIn("stopped responding", body["error"])
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_extract_cancel")

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_records_agent_counts(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "cancelled", "files": 7, "skipped": 2}
        session = self._make_extract_session(status=FileTransferStatus.TRANSFERRING)
        response = self.client.post(
            self._session_url("cancel_file_extract", session.session_id)
        )
        body = response.json()
        self.assertEqual(body["status"], FileTransferStatus.CANCELLED)
        self.assertEqual((body["files_done"], body["files_skipped"]), (7, 2))
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_extract_cancel")
        # a second cancel is a no-op
        mock_nats_cmd.reset_mock()
        response = self.client.post(
            self._session_url("cancel_file_extract", session.session_id)
        )
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        mock_nats_cmd.assert_not_called()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_does_not_overwrite_agent_failure(self, mock_nats_cmd) -> None:
        """The agent's failure lands after the view read the session as active."""
        session = self._make_extract_session(status=FileTransferStatus.TRANSFERRING)
        FileTransferSession.objects.filter(pk=session.pk).update(
            status=FileTransferStatus.FAILED, error_message="The ZIP is damaged"
        )
        with patch("agents.views.get_object_or_404", return_value=session):
            response = self.client.post(
                self._session_url("cancel_file_extract", session.session_id)
            )
        self.assertEqual(response.json()["status"], FileTransferStatus.FAILED)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.FAILED)
        self.assertEqual(session.error_message, "The ZIP is damaged")
        mock_nats_cmd.assert_not_called()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_cancel_offline_agent_skips_nats(self, mock_nats_cmd) -> None:
        self.agent.last_seen = djangotime.now() - dt.timedelta(days=1)
        self.agent.save(update_fields=["last_seen"])
        session = self._make_extract_session()
        response = self.client.post(
            self._session_url("cancel_file_extract", session.session_id)
        )
        self.assertEqual(response.json()["status"], FileTransferStatus.CANCELLED)
        mock_nats_cmd.assert_not_called()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_expiry_task(self, mock_nats_cmd) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        mock_nats_cmd.return_value = {"status": "cancelled"}
        stale = self._make_extract_session(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=500,
            expires_at=djangotime.now() - dt.timedelta(seconds=1),
        )
        fresh = self._make_extract_session(
            status=FileTransferStatus.TRANSFERRING,
            expires_at=djangotime.now() + dt.timedelta(minutes=5),
        )
        self.assertEqual(expire_stale_file_transfer_sessions(), 1)
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(stale.status, FileTransferStatus.EXPIRED)
        self.assertIn("stopped responding", stale.error_message)
        self.assertEqual(fresh.status, FileTransferStatus.TRANSFERRING)
        self.assertEqual(mock_nats_cmd.call_args[0][0]["func"], "files_extract_cancel")


class TestAgentExtractCallbacks(BaseFileBrowserAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.session = self._make_transfer_session(
            operation=FileTransferOperation.EXTRACT,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            total_size=0,
            chunk_size=0,
            expires_at=djangotime.now() + dt.timedelta(minutes=1),
        )
        self.agent_user = self.authenticate_agent(self.agent)
        self.progress_url = reverse(
            "file_transfer_extract_progress", args=[self.session.session_id]
        )
        self.done_url = reverse(
            "file_transfer_extract_done", args=[self.session.session_id]
        )

    def test_progress_then_done(self) -> None:
        response = self.client.post(
            self.progress_url,
            {"written": 100, "total": 1000, "files_done": 1, "files_total": 9},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, FileTransferStatus.TRANSFERRING)
        self.assertEqual(
            (self.session.committed_offset, self.session.total_size), (100, 1000)
        )
        self.assertEqual((self.session.files_done, self.session.files_total), (1, 9))
        self.assertGreater(
            self.session.expires_at, djangotime.now() + dt.timedelta(minutes=5)
        )

        response = self.client.post(
            self.done_url,
            {
                "files": 8,
                "skipped": 1,
                "total": 1000,
                "files_total": 9,
                "warnings": ["skipped symlink a"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, FileTransferStatus.COMPLETED)
        self.assertEqual(self.session.committed_offset, 1000)
        self.assertEqual((self.session.files_done, self.session.files_skipped), (8, 1))
        self.assertEqual(json.loads(self.session.warnings), ["skipped symlink a"])

        # anything after the end is refused so the agent stops
        response = self.client.post(self.progress_url, {"written": 1}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_done_with_error(self) -> None:
        response = self.client.post(
            self.done_url,
            {
                "error": "This ZIP is password-protected, which isn't supported.",
                "files": 0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, FileTransferStatus.FAILED)
        self.assertIn("password-protected", self.session.error_message)

    def test_callbacks_after_cancel_get_409(self) -> None:
        FileTransferSession.objects.filter(pk=self.session.pk).update(
            status=FileTransferStatus.CANCELLED, files_done=3
        )
        for url in (self.progress_url, self.done_url):
            response = self.client.post(url, {"files": 9, "written": 5}, format="json")
            self.assertEqual(response.status_code, 409)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, FileTransferStatus.CANCELLED)
        self.assertEqual(self.session.files_done, 3)

    def test_done_does_not_overwrite_cancel_race(self) -> None:
        """The view still has the row from before the cancel."""
        FileTransferSession.objects.filter(pk=self.session.pk).update(
            status=FileTransferStatus.CANCELLED
        )
        with patch(
            "apiv3.file_transfer_views.get_object_or_404", return_value=self.session
        ):
            response = self.client.post(self.done_url, {"files": 1}, format="json")
        self.assertEqual(response.status_code, 409)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, FileTransferStatus.CANCELLED)

    def test_other_agent_and_other_operation_get_404(self) -> None:
        other = baker.make(
            Agent, version="2.12.0", plat="linux", agent_id="other-agent"
        )
        self.authenticate_agent(other)
        response = self.client.post(self.progress_url, {"written": 1}, format="json")
        self.assertEqual(response.status_code, 404)

        self.client.force_authenticate(user=self.agent_user)
        download = self._make_transfer_session(operation=FileTransferOperation.DOWNLOAD)
        response = self.client.post(
            reverse("file_transfer_extract_done", args=[download.session_id]),
            {"files": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class TestFileExtractPermissions(BaseFileBrowserAPITest):
    """Extract follows the File Browser rules: the role needs Use File
    Browser and the agent must be in the user's clients/sites."""

    body = {
        "source_path": r"C:\Users\Public\Bundle.zip",
        "destination_path": r"C:\Users\Public\Bundle",
    }

    def setUp(self) -> None:
        super().setUp()
        self.other_agent = baker.make(
            Agent,
            version="2.12.0",
            plat="windows",
            agent_id="filebrowser-test-agent-id-0002",
            last_seen=djangotime.now(),
        )
        self.assertNotEqual(self.agent.client, self.other_agent.client)

    def _urls(self, agent, session_id):
        return {
            ("post", "init"): reverse("init_file_extract", args=[agent.agent_id]),
            ("get", "status"): reverse(
                "get_file_extract_status", args=[agent.agent_id, session_id]
            ),
            ("post", "cancel"): reverse(
                "cancel_file_extract", args=[agent.agent_id, session_id]
            ),
            ("get", "list"): reverse("list_file_transfers", args=[agent.agent_id]),
        }

    def _session(self, user, agent=None):
        return self._make_transfer_session(
            agent=agent or self.agent,
            user=user,
            operation=FileTransferOperation.EXTRACT,
            status=FileTransferStatus.TRANSFERRING,
            source_path=self.body["source_path"],
            destination_path=self.body["destination_path"],
            filename="Bundle.zip",
            total_size=0,
            chunk_size=0,
        )

    def _assert_all(self, user_or_none, agent, session, expected, api_key=None):
        # keep the per-agent slot cap out of it
        FileTransferSession.objects.exclude(pk=session.pk).delete()
        if api_key:
            self.client.force_authenticate(user=None)
            self.client.credentials(HTTP_X_API_KEY=api_key)
        else:
            self.client.force_authenticate(user=user_or_none)
        for (method, name), url in self._urls(agent, session.session_id).items():
            data = self.body if name == "init" else {}
            r = getattr(self.client, method)(url, data, format="json")
            want = expected[name] if isinstance(expected, dict) else expected
            self.assertEqual(r.status_code, want, f"{name}: {r.content[:200]}")
        self.client.credentials()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_role_permission_and_agent_scope(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        user = self.create_user_with_roles([])
        session = self._session(user)

        self._assert_all(user, self.agent, session, 403)
        for perm in ("can_use_mesh", "can_list_agents", "can_edit_agent"):
            setattr(user.role, perm, True)
        user.role.save()
        self._assert_all(user, self.agent, session, 403)

        user.role.can_use_file_browser = True
        user.role.save()
        allowed = {"init": 202, "status": 200, "cancel": 200, "list": 200}
        self._assert_all(user, self.agent, session, allowed)

        user.role.can_view_clients.set([self.other_agent.client])
        user.role.save()
        self._assert_all(user, self.agent, self._session(user), 403)
        other_session = self._session(user, self.other_agent)
        self._assert_all(user, self.other_agent, other_session, allowed)

        user.role.can_view_clients.clear()
        user.role.can_view_sites.set([self.agent.site])
        user.role.save()
        self._assert_all(user, self.other_agent, self._session(user), 403)
        self._assert_all(user, self.agent, self._session(user), allowed)

    def test_installer_user_is_refused(self) -> None:
        user = self.create_user_with_roles(["can_use_file_browser"])
        user.is_installer_user = True
        user.save(update_fields=["is_installer_user"])
        self._assert_all(user, self.agent, self._session(user), 403)

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_api_key_follows_the_key_users_role(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        user = self.create_user_with_roles([])
        key = baker.make("accounts.APIKey", user=user, key="EXTRACTTESTKEY1").key
        self._assert_all(None, self.agent, self._session(user), 403, api_key=key)

        user.role.can_use_file_browser = True
        user.role.save()
        allowed = {"init": 202, "status": 200, "cancel": 200, "list": 200}
        self._assert_all(None, self.agent, self._session(user), allowed, api_key=key)

        user.role.can_view_clients.set([self.other_agent.client])
        user.role.save()
        self._assert_all(None, self.agent, self._session(user), 403, api_key=key)

        user.is_active = False
        user.save(update_fields=["is_active"])
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_X_API_KEY=key)
        r = self.client.post(
            reverse("init_file_extract", args=[self.agent.agent_id]),
            self.body,
            format="json",
        )
        self.assertIn(r.status_code, (401, 403))
        self.client.credentials()

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_sessions_are_owner_only_even_for_superusers(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        owner = self.create_user_with_roles(["can_use_file_browser"])
        session = self._session(owner)
        for other in (
            self.create_user_with_roles(["can_use_file_browser"]),
            self.alice,
        ):
            self._assert_all(
                other,
                self.agent,
                session,
                {"init": 202, "status": 404, "cancel": 404, "list": 200},
            )
            self.client.force_authenticate(user=other)
            listed = self.client.get(
                reverse("list_file_transfers", args=[self.agent.agent_id])
            ).json()["transfers"]
            self.assertNotIn(str(session.session_id), [t["session_id"] for t in listed])
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)

    def test_session_cannot_be_reached_through_another_agent(self) -> None:
        session = self._session(self.john)
        for name in ("get_file_extract_status", "cancel_file_extract"):
            url = reverse(name, args=[self.other_agent.agent_id, session.session_id])
            method = self.client.get if name.startswith("get") else self.client.post
            self.assertEqual(method(url).status_code, 404)

    def test_old_agent_version_is_refused(self) -> None:
        self.agent.version = "2.11.0"
        self.agent.save(update_fields=["version"])
        r = self.client.post(
            reverse("init_file_extract", args=[self.agent.agent_id]),
            self.body,
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("2.12.0", r.json())
        self.assertFalse(FileTransferSession.objects.exists())

    def test_agent_callbacks_need_that_agents_token(self) -> None:
        from rest_framework.authtoken.models import Token

        session = self._session(self.john)
        urls = [
            reverse(name, args=[session.session_id])
            for name in ("file_transfer_extract_progress", "file_transfer_extract_done")
        ]
        body = {"files": 1, "written": 1, "error": "x"}

        # no credentials
        self.client.force_authenticate(user=None)
        for url in urls:
            self.assertEqual(
                self.client.post(url, body, format="json").status_code, 401
            )

        # a dashboard user's DRF token is not an agent
        token = Token.objects.create(user=self.john)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        for url in urls:
            self.assertEqual(
                self.client.post(url, body, format="json").status_code, 404
            )

        # another agent's token
        self.client.credentials()
        self.authenticate_agent(self.other_agent)
        for url in urls:
            self.assertEqual(
                self.client.post(url, body, format="json").status_code, 404
            )

        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.TRANSFERRING)
        self.assertEqual(session.files_done, 0)


class TestExtractDoesNotUseTransferRedis(BaseFileBrowserAPITest):
    """Extract keeps its state in the database only: nothing in its
    lifecycle may touch the chunk relay's Redis."""

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_full_lifecycle_never_touches_relay_redis(self, mock_nats_cmd) -> None:
        from agents.tasks import expire_stale_file_transfer_sessions

        mock_nats_cmd.return_value = {"status": "extracting"}
        body = {
            "source_path": r"C:\Users\Public\a.zip",
            "destination_path": r"C:\Users\Public\a",
        }
        with patch(
            "agents.file_transfer_relay._redis_client",
            side_effect=AssertionError("extract used the relay's Redis"),
        ):
            sids = []
            for _ in range(3):
                r = self.client.post(
                    reverse("init_file_extract", args=[self.agent.agent_id]),
                    body,
                    format="json",
                )
                self.assertEqual(r.status_code, 202)
                sids.append(r.json()["session_id"])
            done, cancelled, expired = sids

            self.client.get(reverse("list_file_transfers", args=[self.agent.agent_id]))
            self.authenticate_agent(self.agent)
            for path, data in (
                ("file_transfer_extract_progress", {"written": 5, "total": 9}),
                ("file_transfer_extract_done", {"files": 1, "total": 9}),
            ):
                r = self.client.post(reverse(path, args=[done]), data, format="json")
                self.assertEqual(r.status_code, 200)
            self.client.force_authenticate(user=self.john)
            mock_nats_cmd.return_value = {"status": "cancelled", "files": 0}
            self.client.post(self._session_url("cancel_file_extract", cancelled))
            FileTransferSession.objects.filter(pk=expired).update(
                expires_at=djangotime.now() - dt.timedelta(seconds=1)
            )
            self.client.get(self._session_url("get_file_extract_status", done))
            self.assertEqual(expire_stale_file_transfer_sessions(), 1)
        statuses = {
            str(sid): st
            for sid, st in FileTransferSession.objects.values_list(
                "session_id", "status"
            )
        }
        self.assertEqual(
            [statuses[s] for s in sids],
            [
                FileTransferStatus.COMPLETED,
                FileTransferStatus.CANCELLED,
                FileTransferStatus.EXPIRED,
            ],
        )


class TestTransferRelayRedisHygiene(TacticalTestCase):
    """Against a real Redis (scratch db 15): every relay key expires on its
    own, and clearing a session leaves nothing behind. Guards against keys
    that would pile up in Redis."""

    DB = 15

    def setUp(self) -> None:
        from django.conf import settings
        from redis import from_url

        self.redis = from_url(
            f"redis://{settings.REDIS_HOST}/{self.DB}", decode_responses=False
        )
        try:
            self.redis.ping()
        except Exception:
            self.skipTest("Redis not reachable")
        self.redis.flushdb()
        patcher = patch(
            "agents.file_transfer_relay._redis_client", return_value=self.redis
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.redis.flushdb)
        from agents import file_transfer_relay as relay

        # the Lua scripts are cached per client
        for fn in (
            relay._store_chunk_redis_script,
            relay._peek_chunk_redis_script,
            relay._store_download_chunk_redis_script,
        ):
            fn.cache_clear()
            self.addCleanup(fn.cache_clear)

    def _assert_all_keys_expire(self) -> None:
        from tacticalrmm.constants import (
            FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
        )

        keys = list(self.redis.scan_iter())
        self.assertTrue(keys)
        for key in keys:
            ttl = self.redis.ttl(key)
            self.assertGreater(ttl, 0, f"{key!r} never expires")
            self.assertLessEqual(ttl, FILE_TRANSFER_REDIS_ACK_TTL_SECONDS)

    def test_upload_keys_expire_and_clear_leaves_nothing(self) -> None:
        from agents import file_transfer_relay as relay
        from tacticalrmm.constants import FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS

        sid, other = uuid4(), uuid4()
        chunk = b"x" * (1 << 20)
        for start in range(0, 4 << 20, 1 << 20):
            self.assertIsNone(
                relay.store_upload_chunk(sid, start, start + len(chunk) - 1, chunk)
            )
        relay.store_upload_chunk(other, 0, len(chunk) - 1, chunk)
        relay.signal_upload_ack(sid, 1 << 20)
        self._assert_all_keys_expire()
        for key in self.redis.scan_iter(match="upload:chunk:*"):
            self.assertLessEqual(
                self.redis.ttl(key), FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS
            )

        # a pulled-and-acked chunk is gone, the rest stay until the session ends
        self.assertEqual(relay.peek_upload_chunk(sid, 0).data, chunk)
        relay.delete_upload_chunk(sid, 0)
        self.assertIsNone(relay.peek_upload_chunk(sid, 0))
        relay.clear_upload_session_redis(sid)
        left = [k.decode() for k in self.redis.scan_iter()]
        self.assertTrue(left)
        self.assertFalse([k for k in left if str(sid) in k], left)
        relay.clear_upload_session_redis(other)
        self.assertEqual(self.redis.dbsize(), 0)

    def test_download_keys_expire_and_clear_leaves_nothing(self) -> None:
        from agents import file_transfer_relay as relay

        sid = uuid4()
        chunk = b"y" * (1 << 20)
        for start in range(0, 4 << 20, 1 << 20):
            self.assertIsNone(
                relay.store_download_chunk(sid, start, start + len(chunk) - 1, chunk)
            )
        # the same offset twice is refused, not stored again
        self.assertIsNotNone(relay.store_download_chunk(sid, 0, len(chunk) - 1, chunk))
        relay.signal_download_ack(sid, 1 << 20)
        self._assert_all_keys_expire()
        self.assertEqual(relay.peek_download_chunk(sid, 0).data, chunk)
        relay.clear_download_session_redis(sid)
        self.assertEqual(self.redis.dbsize(), 0)

    def test_rollback_restores_offset_without_leaving_chunks(self) -> None:
        from agents import file_transfer_relay as relay

        sid = uuid4()
        relay.store_upload_chunk(sid, 0, 9, b"0123456789")
        relay.rollback_upload_chunk(sid, 0, 0)
        self.assertEqual(relay.get_accepted_offset(sid), 0)
        self.assertFalse(list(self.redis.scan_iter(match="upload:chunk:*")))
        self._assert_all_keys_expire()


class TestFileExtractHostileInput(BaseFileBrowserAPITest):
    """Malformed or hostile bodies get a clean 400 and never reach the agent."""

    api_name = "init_file_extract"

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_bad_bodies_are_rejected_without_a_session(self, mock_nats_cmd) -> None:
        good = {
            "source_path": r"C:\Users\Public\a.zip",
            "destination_path": r"C:\Users\Public\a",
        }
        bodies = [
            [],
            "a string",
            {**good, "source_path": ["C:\\a.zip"]},
            {**good, "source_path": {"x": 1}},
            {**good, "destination_path": None},
            {**good, "destination_path": 12},
            {**good, "conflict_policy": ["skip"]},
            {**good, "conflict_policy": "overwrite"},
            {**good, "source_path": "C:\\Users\\Public\\a\x00.zip"},
            {**good, "source_path": "C:\\Users\\Public\\a\n.zip"},
            {**good, "destination_path": "C:\\Users\\Public\\a\rb"},
            {**good, "destination_path": "C:\\Users\\..\\Windows"},
            {**good, "destination_path": "C:Users\\Public"},
            {**good, "destination_path": "/etc/x"},
            {**good, "source_path": "C:\\Users\\Public\\a.zip\\"},
            {**good, "source_path": "C:\\Users\\Public\\a.zip:stream"},
            {**good, "source_path": "C:\\Users\\Public\\" + "a" * 300 + ".zip"},
            {**good, "destination_path": "C:\\" + "d" * 5000},
            {**good, "source_path": ""},
            {},
        ]
        for body in bodies:
            r = self.client.post(self.url, body, format="json")
            self.assertEqual(r.status_code, 400, f"{body!r:.120}: {r.content[:120]}")
        mock_nats_cmd.assert_not_called()
        self.assertFalse(FileTransferSession.objects.exists())

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_unusual_but_valid_paths(self, mock_nats_cmd) -> None:
        mock_nats_cmd.return_value = {"status": "extracting"}
        for src, dest in (
            (r"C:\Users\Public\Ünïcødé  spaces.ZIP", r"D:\Ziel mit Leerzeichen\日本"),
            (r"\\fileserver\share\drop\a.zip", r"\\fileserver\share\drop\a"),
            ("C:/Users/Public/forward.zip", "C:/Users/Public/forward"),
            (r"C:\a.zip", "C:\\"),
        ):
            r = self.client.post(
                self.url, {"source_path": src, "destination_path": dest}, format="json"
            )
            self.assertEqual(r.status_code, 202, f"{src} -> {dest}: {r.content}")
            # keep the per-agent cap out of it
            FileTransferSession.objects.all().delete()
        payloads = [c[0][0]["payload"] for c in mock_nats_cmd.call_args_list]
        self.assertEqual(payloads[2]["source_path"], r"C:\Users\Public\forward.zip")
        self.assertEqual(payloads[3]["destination_path"], "C:\\")

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_duplicate_init_creates_independent_sessions(self, mock_nats_cmd) -> None:
        """A double click starts two extractions (each gets its own partial
        names on the agent); the per-agent cap still applies."""
        mock_nats_cmd.return_value = {"status": "extracting"}
        body = {
            "source_path": r"C:\Users\Public\a.zip",
            "destination_path": r"C:\Users\Public\a",
        }
        codes = [
            self.client.post(self.url, body, format="json").status_code
            for _ in range(4)
        ]
        self.assertEqual(codes, [202, 202, 202, 429])
        sids = {c[0][0]["payload"]["session_id"] for c in mock_nats_cmd.call_args_list}
        self.assertEqual(len(sids), 3)

    def test_agent_callbacks_tolerate_garbage(self) -> None:
        session = self._make_transfer_session(
            operation=FileTransferOperation.EXTRACT,
            status=FileTransferStatus.TRANSFERRING,
            total_size=0,
            chunk_size=0,
        )
        self.authenticate_agent(self.agent)
        progress = reverse("file_transfer_extract_progress", args=[session.session_id])
        done = reverse("file_transfer_extract_done", args=[session.session_id])
        for body in (
            [],
            {"written": "lots", "total": -5, "files_done": None},
            {"written": 2**70, "files_done": 2**40},
        ):
            r = self.client.post(progress, body, format="json")
            self.assertEqual(r.status_code, 200, r.content)
        session.refresh_from_db()
        self.assertGreaterEqual(session.committed_offset, 0)
        self.assertGreaterEqual(session.total_size, 0)
        r = self.client.post(
            done,
            {"files": "x", "warnings": ["w"] * 10_000, "error": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, FileTransferStatus.COMPLETED)
        self.assertLessEqual(len(session.warnings), 8192)
        self.assertIsInstance(json.loads(session.warnings), list)


class TestOutOfRangeBodies(BaseFileBrowserAPITest):
    """Values the database can't store get a 400, never a 500."""

    @patch("agents.models.Agent.nats_cmd", new_callable=AsyncMock)
    def test_upload_total_size_too_large(self, mock_nats_cmd) -> None:
        url = reverse("init_file_upload", args=[self.agent.agent_id])
        r = self.client.post(
            url,
            {
                "filename": "a.txt",
                "destination_path": r"C:\Users\Public",
                "total_size": 2**63,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        mock_nats_cmd.assert_not_called()
        self.assertFalse(FileTransferSession.objects.exists())

    @patch("apiv3.file_transfer_views.clear_download_session_redis")
    def test_agent_strings_with_nul_and_huge_sizes(self, _clear) -> None:
        self.authenticate_agent(self.agent)
        failing = self._make_transfer_session(operation=FileTransferOperation.DOWNLOAD)
        r = self.client.post(
            reverse("file_transfer_fail", args=[failing.session_id]),
            {"error": "disk\x00 full"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        failing.refresh_from_db()
        self.assertEqual(failing.error_message, "disk full")

        archive = self._make_transfer_session(
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
        )
        url = reverse("file_transfer_archive_ready", args=[archive.session_id])
        for body in (
            {"total_size": 2**63, "archive_path": r"C:\t.zip"},
            {"total_size": 10, "archive_path": "C:\\" + "a" * 5000},
        ):
            r = self.client.post(url, body, format="json")
            self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post(
            url,
            {
                "total_size": 10,
                "archive_path": "C:\\t\x00.zip",
                "warnings": ["C:\\" + "x" * 150] * 60,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        archive.refresh_from_db()
        self.assertEqual(archive.destination_path, r"C:\t.zip")
        warnings = json.loads(archive.warnings)
        self.assertTrue(0 < len(warnings) < 60)
        self.assertLessEqual(len(archive.warnings), 8192)
