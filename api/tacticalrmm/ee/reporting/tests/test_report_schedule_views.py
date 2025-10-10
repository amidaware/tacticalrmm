import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from model_bakery import baker

from ..models import ReportSchedule, ReportHistory, ReportTemplate
from core.models import Schedule


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
def unauthorized_client():
    client = APIClient()
    user = baker.make("accounts.User", is_superuser=False)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def report_schedule():
    return baker.make(ReportSchedule)


@pytest.fixture
def report_history():
    return baker.make(ReportHistory)


# report schedule views
@pytest.mark.django_db
class TestReportScheduleViews:
    def test_list_schedules(self, authenticated_client):
        baker.make(ReportSchedule, _quantity=3)
        url = "/reporting/schedules/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_create_schedule(self, authenticated_client):
        template = baker.make(ReportTemplate)
        schedule = baker.make(Schedule)
        payload = {
            "name": "Monthly Sales Report",
            "report_template": template.pk,
            "schedule": schedule.pk,
            "format": "pdf",
            "send_report_email": True,
        }
        url = "/reporting/schedules/"
        response = authenticated_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert ReportSchedule.objects.count() == 1
        assert response.data["name"] == "Monthly Sales Report"

    def test_retrieve_schedule(self, authenticated_client, report_schedule):
        url = f"/reporting/schedules/{report_schedule.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == report_schedule.pk

    def test_update_schedule(self, authenticated_client, report_schedule):
        payload = {"name": "Updated Schedule Name"}
        url = f"/reporting/schedules/{report_schedule.id}/"
        response = authenticated_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        report_schedule.refresh_from_db()
        assert report_schedule.name == "Updated Schedule Name"

    def test_delete_schedule(self, authenticated_client, report_schedule):
        url = f"/reporting/schedules/{report_schedule.id}/"
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert not ReportSchedule.objects.filter(pk=report_schedule.pk).exists()


@pytest.mark.django_db
class TestRunReportScheduleView:
    @patch("ee.reporting.views.run_scheduled_report", return_value=(None, None))
    def test_run_schedule_success(
        self, mock_run, authenticated_client, report_schedule
    ):
        url = f"/reporting/schedules/{report_schedule.id}/run/"
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        mock_run.assert_called_once_with(
            schedule=report_schedule, user=authenticated_client.handler._force_user
        )

    @patch(
        "ee.reporting.views.run_scheduled_report",
        return_value=(None, "Something went wrong"),
    )
    def test_run_schedule_with_error(
        self, mock_run, authenticated_client, report_schedule
    ):
        url = f"/reporting/schedules/{report_schedule.id}/run/"
        response = authenticated_client.post(url)

        assert response.status_code == 400
        assert response.data == "Something went wrong"

        mock_run.assert_called_once_with(
            schedule=report_schedule, user=authenticated_client.handler._force_user
        )


@pytest.mark.django_db
class TestReportHistoryViews:
    def test_list_history(self, authenticated_client):
        baker.make(ReportHistory, _quantity=5)
        url = "/reporting/history/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_delete_history(self, authenticated_client, report_history):
        url = f"/reporting/history/{report_history.id}/"
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert not ReportHistory.objects.filter(pk=report_history.pk).exists()


@pytest.mark.django_db
class TestRunReportHistoryView:
    @patch("ee.reporting.views.generate_pdf", return_value=b"pdf_content")
    @patch("ee.reporting.views.normalize_asset_url", return_value="<html></html>")
    def test_run_history_as_pdf(
        self, mock_normalize, mock_pdf, authenticated_client, report_history
    ):
        url = f"/reporting/history/{report_history.id}/run/"
        payload = {"format": "pdf"}
        response = authenticated_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert b"".join(response.streaming_content) == b"pdf_content"
        mock_normalize.assert_called_once_with(report_history.report_data, "pdf")
        mock_pdf.assert_called_once_with(html="<html></html>")

    @patch("ee.reporting.views.normalize_asset_url", return_value="<html></html>")
    def test_run_history_as_html(
        self, mock_normalize, authenticated_client, report_history
    ):
        url = f"/reporting/history/{report_history.id}/run/"
        payload = {"format": "html"}
        response = authenticated_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == "<html></html>"
        mock_normalize.assert_called_once_with(report_history.report_data, "html")

    def test_run_history_with_bad_format(self, authenticated_client, report_history):
        url = f"/reporting/history/{report_history.id}/run/"
        payload = {"format": "invalid"}
        response = authenticated_client.post(url, payload, format="json")

        assert response.status_code == 400
        assert response.data == "Report format is incorrect."


@pytest.mark.django_db
class TestReportSchedulesViewsUnauthorized:
    LIST_CREATE_URL = "/reporting/schedules/"

    def get_detail_url(self, pk):
        return f"/reporting/schedules/{pk}/"

    def get_run_url(self, pk):
        return f"/reporting/schedules/{pk}/run/"

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_schedule_list_permissions(self, request, client_fixture, expected_status):
        client = request.getfixturevalue(client_fixture)
        response = client.get(self.LIST_CREATE_URL)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_schedule_detail_permissions(
        self, request, client_fixture, expected_status, report_schedule
    ):
        client = request.getfixturevalue(client_fixture)
        url = self.get_detail_url(report_schedule.pk)

        get_response = client.get(url)
        put_response = client.put(url, {}, format="json")
        delete_response = client.delete(url)

        assert get_response.status_code == expected_status
        assert put_response.status_code == expected_status
        assert delete_response.status_code == expected_status

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_run_schedule_permissions(
        self, request, client_fixture, expected_status, report_schedule
    ):
        client = request.getfixturevalue(client_fixture)
        url = self.get_run_url(report_schedule.pk)
        response = client.post(url)
        assert response.status_code == expected_status


@pytest.mark.django_db
class TestReportHistoryViewsUnauthorized:
    LIST_URL = "/reporting/history/"

    def get_detail_url(self, pk):
        return f"/reporting/history/{pk}/"

    def get_run_url(self, pk):
        return f"/reporting/history/{pk}/run/"

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_history_list_permissions(self, request, client_fixture, expected_status):
        client = request.getfixturevalue(client_fixture)
        response = client.get(self.LIST_URL)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_history_delete_permissions(
        self, request, client_fixture, expected_status, report_history
    ):
        client = request.getfixturevalue(client_fixture)
        url = self.get_detail_url(report_history.pk)
        response = client.delete(url)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "client_fixture, expected_status",
        [
            ("unauthenticated_client", status.HTTP_401_UNAUTHORIZED),
            ("unauthorized_client", status.HTTP_403_FORBIDDEN),
        ],
    )
    def test_run_history_permissions(
        self, request, client_fixture, expected_status, report_history
    ):
        client = request.getfixturevalue(client_fixture)
        url = self.get_run_url(report_history.pk)
        payload = {"format": "pdf"}
        response = client.post(url, payload, format="json")
        assert response.status_code == expected_status
