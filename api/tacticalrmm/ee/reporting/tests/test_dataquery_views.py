"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import json
from unittest.mock import mock_open, patch

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from ..models import ReportDataQuery


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
def report_data_query():
    return baker.make("reporting.ReportDataQuery")


@pytest.fixture
def report_data_query_data():
    return {"name": "Test Data Query", "json_query": {"test": "value"}}


@pytest.mark.django_db
class TestGetAddReportDataQuery:
    def test_get_all_report_data_queries(self, authenticated_client, report_data_query):
        url = "/reporting/dataqueries/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == report_data_query.name

    def test_post_new_report_data_query(
        self, authenticated_client, report_data_query_data
    ):
        url = "/reporting/dataqueries/"
        response = authenticated_client.post(
            url, data=report_data_query_data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert ReportDataQuery.objects.filter(
            name=report_data_query_data["name"]
        ).exists()

    def test_post_invalid_data(self, authenticated_client):
        url = "/reporting/dataqueries/"
        response = authenticated_client.post(url, data={"name": ""})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_get_data_queries_view(self, unauthenticated_client):
        response = unauthenticated_client.get("/reporting/dataqueries/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_add_data_query_view(self, unauthenticated_client):
        response = unauthenticated_client.post("/reporting/dataqueries/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetEditDeleteReportDataQuery:
    def test_get_specific_report_data_query(
        self, authenticated_client, report_data_query
    ):
        url = f"/reporting/dataqueries/{report_data_query.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == report_data_query.name

    def test_get_non_existent_data_query(self, authenticated_client):
        url = "/reporting/dataqueries/9999/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_update_report_data_query(
        self, authenticated_client, report_data_query, report_data_query_data
    ):
        url = f"/reporting/dataqueries/{report_data_query.id}/"
        response = authenticated_client.put(
            url, data=report_data_query_data, format="json"
        )

        report_data_query.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert report_data_query.name == report_data_query_data["name"]

    def test_put_invalid_data(self, authenticated_client, report_data_query):
        url = f"/reporting/dataqueries/{report_data_query.id}/"
        response = authenticated_client.put(url, data={"name": ""})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_report_data_query(self, authenticated_client, report_data_query):
        url = f"/reporting/dataqueries/{report_data_query.id}/"
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert not ReportDataQuery.objects.filter(id=report_data_query.id).exists()

    def test_delete_non_existent_data_query(self, authenticated_client):
        url = "/reporting/dataqueries/9999/"
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_get_data_queries_view(
        self, unauthenticated_client, report_data_query
    ):
        response = unauthenticated_client.get(
            f"/reporting/dataqueries/{report_data_query.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_edit_html_template_view(
        self, unauthenticated_client, report_data_query
    ):
        response = unauthenticated_client.put(
            f"/reporting/dataqueries/{report_data_query.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_delete_html_template_view(
        self, unauthenticated_client, report_data_query
    ):
        response = unauthenticated_client.delete(
            f"/reporting/dataqueries/{report_data_query.id}/"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestQuerySchema:
    def test_get_query_schema(self, settings, authenticated_client):

        expected_data = {"sample": "json"}

        # mock the file
        mopen = mock_open(read_data=json.dumps({"sample": "json"}))
        with patch("builtins.open", mopen):
            response = authenticated_client.get("/reporting/queryschema/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_data

    def test_get_query_schema_file_missing(self, settings, authenticated_client):
        # Set DEBUG mode
        settings.DEBUG = True

        with patch("builtins.open", side_effect=FileNotFoundError):
            response = authenticated_client.get("/reporting/queryschema/")
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_query_schema_view(self, unauthenticated_client):
        response = unauthenticated_client.delete("/reporting/queryschema/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
