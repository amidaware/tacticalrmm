"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import base64
import json
import uuid
from unittest.mock import patch

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from ..models import ReportAsset, ReportHTMLTemplate, ReportTemplate


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = baker.make("accounts.User", is_superuser=True)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.fixture
def report_template():
    return baker.make(
        "reporting.ReportTemplate",
        name="test_template",
        template_md="# Test MD",
        template_css="body { color: red; }",
        type="markdown",
        depends_on=["some_dependency"],
    )


@pytest.fixture
def report_template_with_base_template():
    base_template = baker.make("reporting.ReportHTMLTemplate")
    return baker.make(
        "reporting.ReportTemplate",
        name="test_template",
        template_md="# Test MD",
        template_css="body { color: red; }",
        template_html=base_template,
        type="markdown",
        depends_on=["some_dependency"],
    )


@pytest.mark.django_db
class TestExportReportTemplate:
    @patch(
        "ee.reporting.views.base64_encode_assets", return_value="some_encoded_assets"
    )
    def test_export_report_template_with_base_template(
        self,
        mock_encode_assets,
        authenticated_client,
        report_template_with_base_template,
    ):
        url = f"/reporting/templates/{report_template_with_base_template.id}/export/"
        response = authenticated_client.post(url)

        expected_response = {
            "base_template": {
                "name": report_template_with_base_template.template_html.name,
                "html": report_template_with_base_template.template_html.html,
            },
            "template": {
                "name": report_template_with_base_template.name,
                "template_css": report_template_with_base_template.template_css,
                "template_md": report_template_with_base_template.template_md,
                "type": report_template_with_base_template.type,
                "depends_on": report_template_with_base_template.depends_on,
                "template_variables": "",
            },
            "assets": "some_encoded_assets",
        }

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response
        mock_encode_assets.assert_called()

    @patch(
        "ee.reporting.views.base64_encode_assets", return_value="some_encoded_assets"
    )
    def test_export_report_template_without_base_template(
        self,
        mock_encode_assets,
        authenticated_client,
        report_template,
    ):
        url = f"/reporting/templates/{report_template.id}/export/"
        response = authenticated_client.post(url)

        expected_response = {
            "base_template": None,
            "template": {
                "name": report_template.name,
                "template_css": report_template.template_css,
                "template_md": report_template.template_md,
                "type": report_template.type,
                "depends_on": report_template.depends_on,
                "template_variables": "",
            },
            "assets": "some_encoded_assets",
        }

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response
        mock_encode_assets.assert_called()

    def test_unauthenticated_export_report_template_view(
        self, unauthenticated_client, report_template
    ):
        response = unauthenticated_client.post(
            f"/reporting/templates/{report_template.id}/export/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestImportReportTemplate:
    @pytest.fixture
    def valid_template_data(self):
        """Returns a sample valid template data."""
        return {
            "template": {
                "name": "test_template",
                "template_md": "# Test MD",
                "type": "markdown",
                "depends_on": ["some_dependency"],
            }
        }

    @pytest.fixture
    def valid_base_template_data(self):
        """Returns a sample valid base template data."""
        return {"name": "base_test_template", "html": "<div>Test</div>"}

    @pytest.fixture
    def valid_assets_data(self):
        """Returns a sample valid assets data."""
        return [
            {
                "id": str(uuid.uuid4()),
                "name": "asset1.png",
                "file": base64.b64encode(b"mock_content1").decode("utf-8"),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "asset2.png",
                "file": base64.b64encode(b"mock_content2").decode("utf-8"),
            },
        ]

    def test_basic_import(self, authenticated_client, valid_template_data):
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportTemplate.objects.filter(name="test_template").exists()

    def test_import_with_base_template(
        self, authenticated_client, valid_template_data, valid_base_template_data
    ):
        valid_template_data["base_template"] = valid_base_template_data
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportHTMLTemplate.objects.filter(name="base_test_template").exists()
        assert ReportTemplate.objects.filter(name="test_template").exists()

    def test_import_with_base_template_with_overwrite(
        self, authenticated_client, valid_template_data, valid_base_template_data
    ):
        valid_template_data["base_template"] = valid_base_template_data
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data), "overwrite": True}
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportHTMLTemplate.objects.filter(name="base_test_template").exists()
        assert ReportTemplate.objects.filter(name="test_template").exists()

        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data), "overwrite": True}
        )

        assert (
            ReportHTMLTemplate.objects.filter(
                name__startswith="base_test_template"
            ).count()
            == 1
        )
        assert (
            ReportTemplate.objects.filter(name__startswith="test_template").count() == 1
        )

    def test_import_with_assets(
        self, authenticated_client, valid_template_data, valid_assets_data
    ):
        valid_template_data["assets"] = valid_assets_data
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportAsset.objects.filter(id=valid_assets_data[0]["id"]).exists()
        assert ReportAsset.objects.filter(id=valid_assets_data[1]["id"]).exists()

    @patch(
        "ee.reporting.utils._generate_random_string",
        return_value="randomized",
    )
    def test_name_conflict_on_repeated_calls(
        self, generate_random_string_mock, authenticated_client, valid_template_data
    ):
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )
        assert ReportTemplate.objects.filter(name="test_template").exists()

        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        print(response.data)
        assert response.status_code == status.HTTP_200_OK
        assert ReportTemplate.objects.filter(name="test_template_randomized").exists()

    def test_invalid_data(self, authenticated_client, valid_template_data):
        valid_template_data["template"].pop("name")
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_import_with_assets_with_conflicting_paths(
        self, authenticated_client, valid_template_data, valid_assets_data
    ):
        conflicting_asset = {
            "id": str(uuid.uuid4()),
            "name": valid_assets_data[0]["name"],
            "file": base64.b64encode(b"mock_content1").decode("utf-8"),
        }
        valid_assets_data.append(conflicting_asset)
        valid_template_data["assets"] = valid_assets_data
        url = "/reporting/templates/import/"
        response = authenticated_client.post(
            url, data={"template": json.dumps(valid_template_data)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportAsset.objects.filter(id=valid_assets_data[0]["id"]).exists()
        assert ReportAsset.objects.filter(id=valid_assets_data[1]["id"]).exists()
        assert ReportAsset.objects.filter(id=conflicting_asset["id"]).exists()

        # check if the renaming logic is working
        asset = ReportAsset.objects.get(id=conflicting_asset["id"])
        assert asset.file.name != valid_assets_data[0]["name"]

    def test_unauthenticated_import_report_template_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/templates/import/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
