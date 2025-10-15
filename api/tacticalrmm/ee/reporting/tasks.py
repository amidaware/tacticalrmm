from typing import List, Optional
from zoneinfo import ZoneInfo

from django.utils import timezone as djangotime

from tacticalrmm.celery import app
from tacticalrmm.logger import logger
from tacticalrmm.scheduler import (
    should_run_daily,
    should_run_monthly,
    should_run_monthly_dow,
    should_run_weekly,
)
from tacticalrmm.utils import get_core_settings, get_default_timezone


@app.task
def prune_report_history_task(older_than_days: int) -> str:
    from .models import ReportHistory

    ReportHistory.objects.filter(
        date_created__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"


@app.task
def scheduled_reports_runner():
    from tacticalrmm.constants import MonthlyType, ScheduleType

    from .models import ReportSchedule
    from .utils import run_scheduled_report

    now = djangotime.now()
    tz = get_default_timezone()

    reports = ReportSchedule.objects.select_related(
        "report_template", "schedule"
    ).filter(enabled=True)

    run_list = []

    for report in reports:
        schedule = report.schedule
        try:
            report_tz = ZoneInfo(report.timezone)
        except Exception:
            report_tz = None

        run = False

        if report.locked_at and report.locked_at > now - djangotime.timedelta(
            seconds=55
        ):
            # prevent race
            logger.error(
                f"Report Schedule for template: {report.report_template.name} already executed too recently, skipping."
            )
            continue

        elif schedule.schedule_type == ScheduleType.DAILY:
            run = should_run_daily(
                run_time=schedule.run_time,
                current_time=now,
                timezone=report_tz or tz,
            )

        elif schedule.schedule_type == ScheduleType.WEEKLY:
            run = should_run_weekly(
                run_time=schedule.run_time,
                weekdays=schedule.run_time_weekdays,
                current_time=now,
                timezone=report_tz or tz,
            )

        elif (
            schedule.schedule_type == ScheduleType.MONTHLY
            and schedule.monthly_type == MonthlyType.DAYS
        ):
            run = should_run_monthly(
                run_time=schedule.run_time,
                days=schedule.monthly_days_of_month,
                months=schedule.monthly_months_of_year,
                current_time=now,
                timezone=report_tz or tz,
            )

        elif (
            schedule.schedule_type == ScheduleType.MONTHLY
            and schedule.monthly_type == MonthlyType.WEEKS
        ):
            run = should_run_monthly_dow(
                run_time=schedule.run_time,
                weekdays=schedule.run_time_weekdays,
                weeks=schedule.monthly_weeks_of_month,
                months=schedule.monthly_months_of_year,
                current_time=now,
                timezone=report_tz or tz,
            )

        if run:
            report.locked_at = djangotime.now()
            report.save(update_fields=["locked_at"])
            run_list.append(report)

    for report in run_list:
        try:
            _, error = run_scheduled_report(schedule=report)
        except Exception as e:
            logger.error(str(e))
        else:
            if error:
                logger.error(error)


@app.task
def email_report(
    template_name: str,
    recipients: List[str] = [],
    body: Optional[str] = None,
    subject: Optional[str] = None,
    attachment_name: Optional[str] = None,
    report_link: Optional[str] = None,
    attachment: Optional[bytes] = None,
    attachment_type: Optional[str] = None,
    attachment_extension: Optional[str] = None,
    include_report_link: Optional[bool] = False,
):
    core = get_core_settings()

    new_subject = subject or f"Scheduled Report: {template_name}"
    new_body = body or "Your report is attached."

    if attachment_type == "html" and include_report_link:
        new_body += f"\n\nView the report online:\n\n{report_link}"

    core.send_mail(
        subject=new_subject,
        body=new_body,
        attachment=attachment,
        attachment_filename=attachment_name or template_name,
        attachment_type=attachment_type,
        attachment_extension=attachment_extension,
        override_recipients=recipients,
    )
