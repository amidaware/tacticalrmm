"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from ..models import ReportHTMLTemplate


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
def report_html_template():
    return baker.make("reporting.ReportHTMLTemplate")


@pytest.fixture
def report_html_template_data():
    return {"name": "Test Template", "html": "<div>Test HTML</div>"}


@pytest.mark.django_db
class TestGetAddReportHTMLTemplate:
    def test_get_all_report_html_templates(
        self, authenticated_client, report_html_template
    ):
        response = authenticated_client.get("/reporting/htmltemplates/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == report_html_template.name

    def test_post_new_report_html_template(
        self, authenticated_client, report_html_template_data
    ):
        response = authenticated_client.post(
            "/reporting/htmltemplates/", data=report_html_template_data
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportHTMLTemplate.objects.filter(
            name=report_html_template_data["name"]
        ).exists()

    def test_post_invalid_data(self, authenticated_client):
        response = authenticated_client.post(
            "/reporting/htmltemplates/", data={"name": ""}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_get_html_templates_view(self, unauthenticated_client):
        response = unauthenticated_client.get("/reporting/htmltemplates/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_add_html_template_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/htmltemplates/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetEditDeleteReportHTMLTemplate:
    def test_get_specific_report_html_template(
        self, authenticated_client, report_html_template
    ):
        response = authenticated_client.get(
            f"/reporting/htmltemplates/{report_html_template.id}/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == report_html_template.name

    def test_get_non_existent_template(self, authenticated_client):
        response = authenticated_client.get("/reporting/htmltemplates/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_update_report_html_template(
        self, authenticated_client, report_html_template, report_html_template_data
    ):
        response = authenticated_client.put(
            f"/reporting/htmltemplates/{report_html_template.id}/",
            data=report_html_template_data,
        )

        report_html_template.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert report_html_template.name == report_html_template_data["name"]

    def test_put_invalid_data(self, authenticated_client, report_html_template):
        response = authenticated_client.put(
            f"/reporting/htmltemplates/{report_html_template.id}/", data={"name": ""}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_report_html_template(
        self, authenticated_client, report_html_template
    ):
        response = authenticated_client.delete(
            f"/reporting/htmltemplates/{report_html_template.id}/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert not ReportHTMLTemplate.objects.filter(
            id=report_html_template.id
        ).exists()

    def test_delete_non_existent_template(self, authenticated_client):
        response = authenticated_client.delete("/reporting/htmltemplates/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_get_html_template_view(
        self, unauthenticated_client, report_html_template
    ):
        response = unauthenticated_client.get(
            f"/reporting/htmltemplates/{report_html_template.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_edit_html_template_view(
        self, unauthenticated_client, report_html_template
    ):
        response = unauthenticated_client.put(
            f"/reporting/htmltemplates/{report_html_template.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_delete_html_template_view(
        self, unauthenticated_client, report_html_template
    ):
        response = unauthenticated_client.delete(
            f"/reporting/htmltemplates/{report_html_template.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
