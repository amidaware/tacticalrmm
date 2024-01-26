"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from unittest.mock import patch

import pytest
from jinja2.exceptions import TemplateError
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient


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
    return baker.make("reporting.ReportTemplate")


@pytest.mark.django_db
class TestReportTemplateViews:
    def test_get_all_report_templates_empty_db(self, authenticated_client):
        response = authenticated_client.get("/reporting/templates/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_get_all_report_templates(self, authenticated_client):
        # Create some sample ReportTemplates using model_bakery
        baker.make("reporting.ReportTemplate", _quantity=5)
        response = authenticated_client.get("/reporting/templates/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_get_report_templates_with_filter(self, authenticated_client):
        # Create templates with specific dependencies
        baker.make("reporting.ReportTemplate", depends_on=["agent"], _quantity=3)
        baker.make("reporting.ReportTemplate", depends_on=["client"], _quantity=2)

        response = authenticated_client.get(
            "/reporting/templates/", {"dependsOn[]": ["agent"]}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_post_report_template_valid_data(self, authenticated_client):
        valid_data = {"name": "Test Template", "template_md": "Template Text"}
        response = authenticated_client.post("/reporting/templates/", valid_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Test Template"

    def test_post_report_template_invalid_data(self, authenticated_client):
        invalid_data = {"name": "Test Template"}
        response = authenticated_client.post("/reporting/templates/", invalid_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_report_template(self, authenticated_client, report_template):
        url = f"/reporting/templates/{report_template.pk}/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == report_template.id

    def test_edit_report_template(self, authenticated_client, report_template):
        url = f"/reporting/templates/{report_template.pk}/"
        updated_name = "Updated name"

        response = authenticated_client.put(url, {"name": updated_name}, format="json")

        assert response.status_code == status.HTTP_200_OK
        report_template.refresh_from_db()
        assert report_template.name == updated_name

    def test_delete_report_template(self, authenticated_client, report_template):
        url = f"/reporting/templates/{report_template.pk}/"
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        with pytest.raises(report_template.DoesNotExist):
            report_template.refresh_from_db()

    # test unauthorized access
    def test_unauthorized_get_report_templates_view(self, unauthenticated_client):
        url = "/reporting/templates/"
        response = unauthenticated_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_add_report_template_view(self, unauthenticated_client):
        url = "/reporting/templates/"
        response = unauthenticated_client.post(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_get_report_template_view(
        self, unauthenticated_client, report_template
    ):
        url = f"/reporting/templates/{report_template.pk}/"
        response = unauthenticated_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_edit_report_template_view(
        self, unauthenticated_client, report_template
    ):
        url = f"/reporting/templates/{report_template.pk}/"
        updated_name = "Updated name"

        response = unauthenticated_client.put(
            url, {"name": updated_name}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_delete_report_template_view(
        self, unauthenticated_client, report_template
    ):
        url = f"/reporting/templates/{report_template.pk}/"
        response = unauthenticated_client.delete(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestReportTemplateGenerateView:
    def test_generate_html_report(self, authenticated_client, report_template):
        data = {"format": "html", "dependencies": {}}
        response = authenticated_client.post(
            f"/reporting/templates/{report_template.id}/run/", data=data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert report_template.template_md in response.data

    def test_generate_pdf_report(self, authenticated_client, report_template):
        data = {"format": "pdf", "dependencies": {}}
        response = authenticated_client.post(
            f"/reporting/templates/{report_template.id}/run/", data=data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response["content-type"] == "application/pdf"

    def test_generate_invalid_format_report(
        self, authenticated_client, report_template
    ):
        data = {"format": "invalid_format", "dependencies": {}}
        response = authenticated_client.post(
            f"/reporting/templates/{report_template.id}/run/", data=data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_report_template_error(self, authenticated_client):
        template = baker.make("reporting.ReportTemplate", template_md="{{invalid}")
        data = {"format": "html", "dependencies": {}}
        response = authenticated_client.post(
            f"/reporting/templates/{template.id}/run/", data=data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_report_with_dependencies(
        self, authenticated_client, report_template
    ):
        sample_html = "<html><body>Sample Report</body></html>"
        data = {"format": "html", "dependencies": {"client": 1}}

        with patch(
            "ee.reporting.views.generate_html", return_value=(sample_html, None)
        ) as mock_generate_html:
            url = f"/reporting/templates/{report_template.id}/run/"
            response = authenticated_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert response.data == sample_html

        mock_generate_html.assert_called_with(
            template=report_template.template_md,
            template_type=report_template.type,
            css=report_template.template_css if report_template.template_css else "",
            html_template=(
                report_template.template_html.id
                if report_template.template_html
                else None
            ),
            variables=report_template.template_variables,
            dependencies={"client": 1},
        )

    def test_unauthenticated_generate_report_view(
        self, unauthenticated_client, report_template
    ):
        response = unauthenticated_client.post(
            f"/reporting/templates/{report_template.id}/run/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGenerateReportPreview:
    def test_generate_report_preview_html_format(self, authenticated_client):
        data = {
            "template_md": "some template md",
            "type": "some type",
            "template_css": "some css",
            "template_variables": {},
            "dependencies": {},
            "format": "html",
            "debug": False,
        }

        with patch(
            "ee.reporting.views.generate_html", return_value=("<html></html>", {})
        ) as mock_generate_html:
            response = authenticated_client.post(
                "/reporting/templates/preview/", data, format="json"
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.data == "<html></html>"
        mock_generate_html.assert_called()

    @patch("ee.reporting.views.generate_html", return_value=("<html></html>", {}))
    @patch("ee.reporting.views.generate_pdf", return_value=b"some_pdf_bytes")
    def test_generate_report_preview_pdf_format(
        self, mock_generate_html, mock_generate_pdf, authenticated_client
    ):
        data = {
            "template_md": "some template md",
            "type": "some type",
            "template_css": "some css",
            "template_variables": {},
            "dependencies": {},
            "format": "pdf",
            "debug": False,
        }

        response = authenticated_client.post(
            "/reporting/templates/preview/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        mock_generate_html.assert_called()
        mock_generate_pdf.assert_called()

    def test_generate_report_preview_debug(self, authenticated_client):
        data = {
            "template_md": "some template md",
            "type": "markdown",
            "template_css": "some css",
            "template_variables": {},
            "dependencies": {},
            "format": "html",
            "debug": True,
        }

        with patch(
            "ee.reporting.views.generate_html",
            return_value=("<html></html>", {"agent": baker.prepare("agents.Agent")}),
        ) as mock_generate_html:
            response = authenticated_client.post(
                "/reporting/templates/preview/", data, format="json"
            )
            assert response.status_code == status.HTTP_200_OK
            assert "template" in response.data
            assert "variables" in response.data
        mock_generate_html.assert_called()

    def test_generate_report_preview_invalid_data(self, authenticated_client):
        data = {
            "template_md": "some template md",
            # Missing 'type'
            "template_css": "some css",
            "template_variables": {},
            "dependencies": {},
            "format": "invalid_format",
            "debug": True,
        }

        response = authenticated_client.post(
            "/reporting/templates/preview/", data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_report_preview_template_error(self, authenticated_client):
        data = {
            "template_md": "some template md",
            "type": "some type",
            "template_css": "some css",
            "template_variables": {},
            "dependencies": {},
            "format": "html",
            "debug": True,
        }

        with patch(
            "ee.reporting.views.generate_html",
            side_effect=TemplateError("Some template error"),
        ):
            response = authenticated_client.post(
                "/reporting/templates/preview/", data, format="json"
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Some template error" in response.data

    def test_unauthenticated_generate_report_preview_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/templates/preview/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetAllowedValues:
    def test_valid_input(self, authenticated_client):
        data = {
            "variables": {
                "user": {
                    "name": "Alice",
                    "roles": ["admin", "user"],
                },
                "count": 1,
            },
            "dependencies": {},
        }

        expected_response_data = {
            "user": "Object",
            "user.name": "str",
            "user.roles": "Array (2 Results)",
            "user.roles[0]": "str",
            "count": "int",
        }

        with patch(
            "ee.reporting.views.prep_variables_for_template",
            return_value=data["variables"],
        ):
            response = authenticated_client.post(
                "/reporting/templates/preview/analysis/", data, format="json"
            )

        assert response.status_code == 200
        assert response.data == expected_response_data

    def test_empty_variables(self, authenticated_client):
        data = {"variables": {}, "dependencies": {}}
        with patch(
            "ee.reporting.views.prep_variables_for_template",
            return_value=data["variables"],
        ):
            response = authenticated_client.post(
                "/reporting/templates/preview/analysis/", data, format="json"
            )

        assert response.status_code == 200
        assert response.data is None

    def test_invalid_input(self, authenticated_client):
        data = {"invalidKey": {}}

        response = authenticated_client.post(
            "/reporting/templates/preview/analysis/", data, format="json"
        )

        assert response.status_code == 400

    def test_unauthenticated_variable_analysis_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/templates/preview/analysis/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
