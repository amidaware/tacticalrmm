"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from unittest.mock import patch

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from ..models import ReportHistory, ReportSchedule, ReportTemplate
from ..utils import (
    ScheduledReportRunResult,
    data_source_keys_referenced_by,
    run_scheduled_report,
)
from core.models import Schedule


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = baker.make("accounts.User", is_superuser=True)
    client.force_authenticate(user=user)
    return client


class TestDataSourceKeysReferencedBy:
    def test_attr_and_item_access(self):
        keys = data_source_keys_referenced_by(
            [
                "data_sources.foo|length > 0",
                'data_sources["bar"] > 1',
                "data_sources['baz']",
            ]
        )
        assert keys == {"foo", "bar", "baz"}

    def test_bare_data_sources_means_all(self):
        assert data_source_keys_referenced_by(["data_sources"]) is None

    def test_no_data_sources_returns_empty(self):
        assert data_source_keys_referenced_by(["True", "1 > 0"]) == set()


@pytest.mark.django_db
class TestRunScheduledReportConditions:
    @pytest.fixture
    def template(self):
        return baker.make(
            ReportTemplate,
            template_md="Hello",
            type="markdown",
            template_variables="",
        )

    @pytest.fixture
    def schedule(self, template):
        return baker.make(
            ReportSchedule,
            report_template=template,
            schedule=baker.make(Schedule),
            format="html",
            send_report_email=True,
            conditions=[],
            dependencies={},
        )

    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.run_report")
    def test_empty_conditions_uses_normal_path(
        self, mock_run_report, mock_email, schedule
    ):
        history = baker.make(ReportHistory, report_template=schedule.report_template)
        mock_run_report.return_value = ("<html></html>", None, history)

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "success"
        mock_run_report.assert_called_once()
        assert mock_run_report.call_args.kwargs["prepared_variables"] is None
        mock_email.assert_called_once()
        schedule.refresh_from_db()
        assert schedule.last_run_status == "success"

    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.process_chart_variables")
    @patch("ee.reporting.utils.process_data_sources")
    @patch("ee.reporting.utils.prep_variables_for_template")
    @patch("ee.reporting.utils.run_report")
    def test_falsy_condition_skips_without_email_or_history(
        self,
        mock_run_report,
        mock_prep,
        mock_process_ds,
        mock_charts,
        mock_email,
        schedule,
    ):
        schedule.conditions = ["False"]
        schedule.save(update_fields=["conditions"])
        mock_prep.return_value = {"data_sources": {}}

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "skipped"
        assert result.skip_index == 0
        mock_run_report.assert_not_called()
        mock_process_ds.assert_not_called()
        mock_charts.assert_not_called()
        mock_email.assert_not_called()
        assert ReportHistory.objects.count() == 0
        schedule.refresh_from_db()
        assert schedule.last_run_status == "skipped"
        assert schedule.last_run is not None

    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.process_chart_variables", side_effect=lambda **kw: kw["variables"])
    @patch("ee.reporting.utils.process_data_sources", side_effect=lambda **kw: kw["variables"])
    @patch("ee.reporting.utils.prep_variables_for_template")
    @patch("ee.reporting.utils.run_report")
    def test_truthy_condition_passes_and_reuses_prepared_variables(
        self,
        mock_run_report,
        mock_prep,
        mock_process_ds,
        mock_charts,
        mock_email,
        schedule,
    ):
        schedule.conditions = ["True"]
        schedule.save(update_fields=["conditions"])
        prepared = {"data_sources": {"foo": []}}
        mock_prep.return_value = prepared
        history = baker.make(ReportHistory, report_template=schedule.report_template)
        mock_run_report.return_value = ("<html></html>", None, history)

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "success"
        mock_prep.assert_called_once()
        assert mock_prep.call_args.kwargs["include_charts"] is False
        mock_process_ds.assert_called_once()
        mock_charts.assert_called_once()
        assert mock_run_report.call_args.kwargs["prepared_variables"] is prepared
        mock_email.assert_called_once()

    @pytest.mark.parametrize(
        "expression",
        ["undefined_name", "undefined_name|length > 0"],
    )
    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.prep_variables_for_template")
    @patch("ee.reporting.utils.run_report")
    def test_condition_exception_is_error_not_skip(
        self, mock_run_report, mock_prep, mock_email, schedule, expression
    ):
        schedule.conditions = [expression]
        schedule.save(update_fields=["conditions"])
        mock_prep.return_value = {}

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "error"
        assert result.error
        mock_run_report.assert_not_called()
        mock_email.assert_not_called()
        schedule.refresh_from_db()
        assert schedule.last_run_status == "error"

    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.prep_variables_for_template")
    @patch("ee.reporting.utils.run_report")
    def test_defined_none_is_skip_not_error(
        self, mock_run_report, mock_prep, mock_email, schedule
    ):
        schedule.conditions = ["value"]
        schedule.save(update_fields=["conditions"])
        mock_prep.return_value = {"value": None}

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "skipped"
        mock_run_report.assert_not_called()
        mock_email.assert_not_called()

    @patch("ee.reporting.tasks.email_report.delay")
    @patch("ee.reporting.utils.run_report")
    def test_render_error_does_not_email(self, mock_run_report, mock_email, schedule):
        history = baker.make(
            ReportHistory,
            report_template=schedule.report_template,
            error_data="boom",
        )
        mock_run_report.return_value = (None, "boom", history)

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "error"
        mock_email.assert_not_called()
        schedule.refresh_from_db()
        assert schedule.last_run_status == "error"
    @patch("ee.reporting.utils.build_queryset")
    @patch("ee.reporting.utils.process_chart_variables")
    def test_skip_only_loads_referenced_data_sources(
        self, mock_charts, mock_build_queryset, schedule
    ):
        schedule.report_template.template_variables = """
data_sources:
  foo:
    model: agent
    only: [hostname]
  bar:
    model: agent
    only: [hostname]
"""
        schedule.report_template.save(update_fields=["template_variables"])
        schedule.conditions = ["data_sources.foo|length > 0"]
        schedule.save(update_fields=["conditions"])
        mock_build_queryset.return_value = []

        result = run_scheduled_report(schedule=schedule)

        assert result.status == "skipped"
        assert mock_build_queryset.call_count == 1
        mock_charts.assert_not_called()


@pytest.mark.django_db
class TestReportScheduleConditionsAPI:
    def test_create_schedule_with_conditions(self, authenticated_client):
        template = baker.make(ReportTemplate)
        schedule = baker.make(Schedule)
        payload = {
            "name": "Conditional Schedule",
            "report_template": template.pk,
            "schedule": schedule.pk,
            "format": "html",
            "send_report_email": True,
            "conditions": ["data_sources.agents|length > 0"],
        }
        response = authenticated_client.post(
            "/reporting/schedules/", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["conditions"] == ["data_sources.agents|length > 0"]
        created = ReportSchedule.objects.get(pk=response.data["id"])
        assert created.conditions == ["data_sources.agents|length > 0"]

    def test_create_schedule_rejects_invalid_condition(self, authenticated_client):
        template = baker.make(ReportTemplate)
        schedule = baker.make(Schedule)
        payload = {
            "name": "Bad Condition",
            "report_template": template.pk,
            "schedule": schedule.pk,
            "format": "html",
            "conditions": ["{% for x in y %}{{ x }}{% endfor %}"],
        }
        response = authenticated_client.post(
            "/reporting/schedules/", payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_without_conditions_defaults_empty(self, authenticated_client):
        template = baker.make(ReportTemplate)
        schedule = baker.make(Schedule)
        payload = {
            "name": "No Conditions",
            "report_template": template.pk,
            "schedule": schedule.pk,
            "format": "pdf",
            "send_report_email": True,
        }
        response = authenticated_client.post(
            "/reporting/schedules/", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["conditions"] == []


@pytest.mark.django_db
class TestRunReportScheduleViewConditions:
    @pytest.fixture
    def report_schedule(self):
        return baker.make(ReportSchedule)

    @patch(
        "ee.reporting.views.run_scheduled_report",
        return_value=ScheduledReportRunResult(status="success"),
    )
    def test_run_schedule_success(
        self, mock_run, authenticated_client, report_schedule
    ):
        url = f"/reporting/schedules/{report_schedule.id}/run/"
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        mock_run.assert_called_once()

    @patch(
        "ee.reporting.views.run_scheduled_report",
        return_value=ScheduledReportRunResult(
            status="skipped", skip_index=0, message="Condition 1 was not true"
        ),
    )
    def test_run_schedule_skipped(
        self, mock_run, authenticated_client, report_schedule
    ):
        url = f"/reporting/schedules/{report_schedule.id}/run/"
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "skipped"
        assert response.data["index"] == 0

    @patch(
        "ee.reporting.views.run_scheduled_report",
        return_value=ScheduledReportRunResult(
            status="error", error="Something went wrong"
        ),
    )
    def test_run_schedule_with_error(
        self, mock_run, authenticated_client, report_schedule
    ):
        url = f"/reporting/schedules/{report_schedule.id}/run/"
        response = authenticated_client.post(url)

        assert response.status_code == 400
        assert response.data == "Something went wrong"
