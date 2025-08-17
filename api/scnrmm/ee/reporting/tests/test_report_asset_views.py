"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import os
import uuid
from unittest.mock import mock_open, patch

import pytest
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from ..models import ReportAsset


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = baker.make("accounts.User", is_superuser=True)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.mark.django_db
class TestGetReportAssets:
    @patch("ee.reporting.views.report_assets_fs")
    def test_valid_path_with_dir_and_files(
        self, mock_report_assets_fs, authenticated_client
    ):
        # Set up the mock behavior for report_assets_fs
        mock_report_assets_fs.listdir.return_value = (["folder1"], ["file1.txt"])
        mock_report_assets_fs.size.return_value = 100
        mock_report_assets_fs.url.return_value = "/mocked/url/to/resource"

        path = "some/valid/path"
        url = f"/reporting/assets/?path={path}"
        expected_response_data = [
            {
                "name": "folder1",
                "path": os.path.join(path, "folder1"),
                "type": "folder",
                "size": None,
                "url": "/mocked/url/to/resource",
            },
            {
                "name": "file1.txt",
                "path": os.path.join(path, "file1.txt"),
                "type": "file",
                "size": "100",
                "url": "/mocked/url/to/resource",
            },
        ]

        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.data == expected_response_data

    @patch("ee.reporting.views.report_assets_fs")
    def test_no_path(self, mock_report_assets_fs, authenticated_client):
        # Set up the mock behavior for report_assets_fs
        mock_report_assets_fs.listdir.return_value = (["folder1"], ["file1.txt"])
        mock_report_assets_fs.size.return_value = 100
        mock_report_assets_fs.url.return_value = "/mocked/url/to/resource"

        url = "/reporting/assets/"
        expected_response_data = [
            {
                "name": "folder1",
                "path": "folder1",
                "type": "folder",
                "size": None,
                "url": "/mocked/url/to/resource",
            },
            {
                "name": "file1.txt",
                "path": "file1.txt",
                "type": "file",
                "size": "100",
                "url": "/mocked/url/to/resource",
            },
        ]

        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.data == expected_response_data

    def test_invalid_path(self, authenticated_client):
        url = "/reporting/assets/?path=some/invalid/path"

        response = authenticated_client.get(url)

        assert response.status_code == 400

    def test_unauthenticated_get_report_assets_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetAllAssets:
    @patch("ee.reporting.views.os.walk")
    def test_general_functionality(self, mock_os_walk, authenticated_client):
        mock_os_walk.return_value = iter(
            [(".", ["subdir"], ["file1.txt"]), ("./subdir", [], ["subdirfile.txt"])]
        )

        asset1 = baker.make("reporting.ReportAsset", file="file1.txt")
        asset2 = baker.make("reporting.ReportAsset", file="subdir/subdirfile.txt")

        expected_data = [
            {
                "type": "folder",
                "name": "Report Assets",
                "path": ".",
                "children": [
                    {
                        "type": "folder",
                        "name": "subdir",
                        "path": "subdir",
                        "children": [
                            {
                                "id": asset2.id,
                                "type": "file",
                                "name": "subdirfile.txt",
                                "path": "subdir/subdirfile.txt",
                                "icon": "description",
                            }
                        ],
                        "selectable": False,
                        "icon": "folder",
                        "iconColor": "yellow-9",
                    },
                    {
                        "id": asset1.id,
                        "type": "file",
                        "name": "file1.txt",
                        "path": "file1.txt",
                        "icon": "description",
                    },
                ],
                "selectable": False,
                "icon": "folder",
                "iconColor": "yellow-9",
            }
        ]

        response = authenticated_client.get("/reporting/assets/all/")
        assert response.status_code == 200
        assert expected_data == response.data

    @patch("ee.reporting.views.os.chdir", side_effect=FileNotFoundError)
    def test_invalid_report_assets_dir(self, mock_os_walk, authenticated_client):
        response = authenticated_client.get("/reporting/assets/all/")

        assert response.status_code == 400

    @patch("ee.reporting.views.os.walk")
    def test_only_folders(self, mock_os_walk, authenticated_client):
        mock_os_walk.return_value = iter(
            [(".", ["subdir"], ["file1.txt"]), ("./subdir", [], ["subdirfile.txt"])]
        )

        baker.make("reporting.ReportAsset", file="file1.txt")
        baker.make("reporting.ReportAsset", file="subdir/subdirfile.txt")

        response = authenticated_client.get("/reporting/assets/all/?onlyFolders=true")

        assert response.status_code == 200
        for node in response.data:
            assert node["type"] != "file"

    def test_unauthenticated_get_report_assets_all_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/all/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRenameAsset:
    def test_rename_file(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.rename",
            return_value="path/to/newname.txt",
        ) as mock_rename, patch(
            "ee.reporting.views.report_assets_fs.isfile", return_value=True
        ), patch(
            "ee.reporting.views.report_assets_fs.exists", return_value=True
        ):
            asset = baker.make("reporting.ReportAsset", file="path/to/file.txt")

            response = authenticated_client.put(
                "/reporting/assets/rename/",
                data={"path": "path/to/file.txt", "newName": "newname.txt"},
            )

            mock_rename.assert_called_with(
                path="path/to/file.txt", new_name="newname.txt"
            )
            assert response.status_code == 200
            assert response.data == "path/to/newname.txt"

            asset.refresh_from_db()
            assert asset.file.name == "path/to/newname.txt"

    def test_rename_folder(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.rename",
            return_value="path/to/newfolder",
        ) as mock_rename, patch(
            "ee.reporting.views.report_assets_fs.isfile", return_value=False
        ), patch(
            "ee.reporting.views.report_assets_fs.exists", return_value=True
        ):
            response = authenticated_client.put(
                "/reporting/assets/rename/",
                data={"path": "path/to/folder", "newName": "newfolder"},
            )

            mock_rename.assert_called_with(path="path/to/folder", new_name="newfolder")
            assert response.status_code == 200
            assert response.data == "path/to/newfolder"

    def test_rename_non_existent_file(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.rename",
            side_effect=OSError("File not found"),
        ) as mock_rename, patch(
            "ee.reporting.views.report_assets_fs.exists", return_value=True
        ):
            response = authenticated_client.put(
                "/reporting/assets/rename/",
                data={
                    "path": "non_existent_path/to/file.txt",
                    "newName": "newname.txt",
                },
            )

            mock_rename.assert_called_with(
                path="non_existent_path/to/file.txt", new_name="newname.txt"
            )
            assert response.status_code == 400

    def test_suspicious_operation(self, authenticated_client):
        response = authenticated_client.put(
            "/reporting/assets/rename/",
            data={"path": "../outside/path", "newName": "newname.txt"},
        )

        assert response.status_code == 400

    def test_unauthenticated_rename_report_asset_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/rename/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestNewFolder:
    def test_create_folder_success(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.createfolder",
            return_value="new/path/to/folder",
        ) as mock_createfolder:
            response = authenticated_client.post(
                "/reporting/assets/newfolder/", data={"path": "new/path/to/folder"}
            )

            mock_createfolder.assert_called_with(path="new/path/to/folder")
            assert response.status_code == 200
            assert response.data == "new/path/to/folder"

    def test_create_folder_missing_path(self, authenticated_client):
        response = authenticated_client.post("/reporting/assets/newfolder/")
        assert response.status_code == 400

    def test_create_folder_os_error(self, authenticated_client):
        response = authenticated_client.post(
            "/reporting/assets/newfolder/", data={"path": "invalid/path"}
        )
        assert response.status_code == 400

    def test_create_folder_suspicious_operation(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.createfolder",
            side_effect=SuspiciousFileOperation("Invalid path"),
        ) as mock_createfolder:
            response = authenticated_client.post(
                "/reporting/assets/newfolder/", data={"path": "../outside/path"}
            )

            mock_createfolder.assert_called_with(path="../outside/path")
            assert response.status_code == 400

    def test_unauthenticated_new_folder_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/newfolder/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDeleteAssets:
    def test_delete_directory_success(self, authenticated_client):
        from ..settings import settings

        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=True
        ), patch("ee.reporting.views.shutil.rmtree") as mock_rmtree:
            asset1 = baker.make("reporting.ReportAsset", file="path/to/dir/file1.txt")
            asset2 = baker.make("reporting.ReportAsset", file="path/to/dir/file2.txt")
            response = authenticated_client.post(
                "/reporting/assets/delete/", data={"paths": ["path/to/dir"]}
            )

            mock_rmtree.assert_called_with(
                f"{settings.REPORTING_ASSETS_BASE_PATH}/path/to/dir"
            )
            assert response.status_code == 200

            # make sure the assets within the deleted folder also got deleted
            assert not ReportAsset.objects.filter(id=asset1.id).exists()
            assert not ReportAsset.objects.filter(id=asset2.id).exists()

    def test_delete_file_success(self, authenticated_client):
        with patch("ee.reporting.views.report_assets_fs.isdir", return_value=False):
            asset = baker.make("reporting.ReportAsset", file="path/to/file.txt")
            response = authenticated_client.post(
                "/reporting/assets/delete/", data={"paths": ["path/to/file.txt"]}
            )

            assert response.status_code == 200
            assert not ReportAsset.objects.filter(id=asset.id).exists()

    def test_delete_os_error(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=True
        ), patch(
            "ee.reporting.views.shutil.rmtree", side_effect=OSError("Unable to delete")
        ):
            response = authenticated_client.post(
                "/reporting/assets/delete/", data={"paths": ["invalid/path"]}
            )

            assert response.status_code == 400

    def test_delete_suspicious_operation(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=True
        ), patch(
            "ee.reporting.views.shutil.rmtree",
            side_effect=SuspiciousFileOperation("Invalid path"),
        ):
            response = authenticated_client.post(
                "/reporting/assets/delete/", data={"paths": ["../outside/path"]}
            )

            assert response.status_code == 400

    def test_delete_asset_not_in_db_but_on_fs(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=False
        ), patch("ee.reporting.views.report_assets_fs.delete") as mock_fs_delete:
            response = authenticated_client.post(
                "/reporting/assets/delete/", data={"paths": ["path/to/file.txt"]}
            )

            mock_fs_delete.assert_called_with("path/to/file.txt")
            assert response.status_code == 200

    def test_unauthenticated_delete_assets_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/delete/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUploadAssets:
    def test_upload_success(self, authenticated_client):
        mock_file = SimpleUploadedFile("test123.txt", b"file_content")

        with patch("ee.reporting.views.report_assets_fs.isdir", return_value=True):
            response = authenticated_client.post(
                "/reporting/assets/upload/",
                data={"parentPath": "path", "test123.txt": mock_file},
            )

            assert response.data["test123.txt"]["filename"] == "path/test123.txt"
            assert response.status_code == 200

            assert ReportAsset.objects.filter(file="path/test123.txt").exists()

            # cleanup file so future tests don't break
            asset = ReportAsset.objects.get(file="path/test123.txt")
            asset.file.delete()
            asset.delete()

    def test_upload_invalid_directory(self, authenticated_client):
        with patch("ee.reporting.views.report_assets_fs.isdir", return_value=False):
            response = authenticated_client.post(
                "/reporting/assets/upload/",
                data={"parentPath": "invalid_path"},
            )
            assert response.status_code == 400

    def test_upload_suspicious_operation(self, authenticated_client):
        mock_file = SimpleUploadedFile("test2.txt", b"file_content")

        with patch("ee.reporting.views.report_assets_fs.isdir", return_value=True):
            response = authenticated_client.post(
                "/reporting/assets/upload/",
                data={"parentPath": "../path", "test2.txt": mock_file},
            )

            assert response.status_code == 400

    def test_unauthenticated_uploads_assets_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/upload/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAssetDownload:
    def test_download_file_success(self, authenticated_client):
        m = mock_open()
        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=False
        ), patch("builtins.open", m), patch(
            "ee.reporting.views.report_assets_fs.path", return_value="path/test.txt"
        ):
            response = authenticated_client.get(
                "/reporting/assets/download/", {"path": "test.txt"}
            )

            assert response.status_code == 200

    def test_download_directory_success(self, authenticated_client):
        m = mock_open()
        with patch(
            "ee.reporting.views.report_assets_fs.isdir", return_value=True
        ), patch(
            "ee.reporting.views.shutil.make_archive", return_value="path/test.zip"
        ), patch(
            "builtins.open", m
        ), patch(
            "ee.reporting.views.report_assets_fs.path", return_value="path/test"
        ), patch(
            "ee.reporting.views.os.remove", return_value=None
        ):
            response = authenticated_client.get(
                "/reporting/assets/download/", {"path": "test"}
            )

            assert response.status_code == 200
            m.assert_called_once_with("path/test.zip", "rb")

    def test_download_invalid_path(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir",
            side_effect=OSError("Path does not exist"),
        ):
            response = authenticated_client.get(
                "/reporting/assets/download/", {"path": "invalid_path"}
            )
            assert response.status_code == 400

    def test_download_os_error(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir",
            side_effect=OSError("Download failed"),
        ):
            response = authenticated_client.get(
                "/reporting/assets/download/", {"path": "test.txt"}
            )
            assert response.status_code == 400

    def test_download_suspicious_operation(self, authenticated_client):
        with patch(
            "ee.reporting.views.report_assets_fs.isdir",
            side_effect=SuspiciousFileOperation("Suspicious path"),
        ):
            response = authenticated_client.get(
                "/reporting/assets/download/", {"path": "test.txt"}
            )
            assert response.status_code == 400

    def test_unauthenticated_uploads_assets_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/assets/download/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAssetNginxRedirect:
    @pytest.fixture
    def asset(self):
        return baker.make("reporting.ReportAsset", file="test_asset.txt")

    def test_valid_uuid_and_path(self, unauthenticated_client, asset):
        response = unauthenticated_client.get(
            f"/reporting/assets/test_asset.txt?id={asset.id}"
        )

        assert response.status_code == 200
        assert response["X-Accel-Redirect"] == "/assets/test_asset.txt"

    def test_valid_uuid_wrong_path(self, unauthenticated_client, asset):
        response = unauthenticated_client.get(
            f"/reporting/assets/wrong_path.txt?id={asset.id}"
        )

        assert response.status_code == 403

    def test_valid_uuid_no_asset(self, unauthenticated_client):
        non_existent_uuid = uuid.uuid4()
        url = f"/reporting/assets/test_asset.txt?id={non_existent_uuid}"
        response = unauthenticated_client.get(url)

        assert response.status_code == 404

    def test_invalid_uuid(self, unauthenticated_client):
        response = unauthenticated_client.get(
            "/reporting/assets/test_asset.txt?id=invalid_uuid"
        )

        assert response.status_code == 400
        assert "There was a error processing the request" in response.content.decode(
            "utf-8"
        )

    def test_no_id(self, unauthenticated_client):
        response = unauthenticated_client.get("/reporting/assets/test_asset.txt")

        assert response.status_code == 400
        assert "There was a error processing the request" in response.content.decode(
            "utf-8"
        )
