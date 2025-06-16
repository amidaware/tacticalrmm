from django.utils import timezone as djangotime
from typing import Optional, List
from tacticalrmm.logger import logger

from tacticalrmm.celery import app
from tacticalrmm.scheduler import (
    should_run_daily,
    should_run_weekly,
    should_run_monthly,
    should_run_monthly_dow,
)
from .models import ReportSchedule
from .utils import run_scheduled_report
from core.models import ScheduleType, MonthlyType
from tacticalrmm.utils import get_default_timezone, get_core_settings


@app.task
def prune_report_history_task(older_than_days: int) -> str:
    from .models import ReportHistory

    ReportHistory.objects.filter(
        date_created__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"


@app.task
def scheduled_reports_runner():
    now = djangotime.now()
    tz = get_default_timezone()

    reports = ReportSchedule.objects.select_related(
        "report_template", "schedule"
    ).filter(enabled=True)

    for report in reports:
        schedule = report.schedule

        run = False

        if report.locked_at and report.locked_at > now - djangotime.timedelta(
            hours=1
        ):
            # prevent race
            logger.error(
                f"Report Schedule for template: {schedule.report_template.name} already executed too recently, skipping."
            )
            continue

        elif schedule.schedule_type == ScheduleType.DAILY:
            run = should_run_daily(
                run_time=schedule.run_time, current_time=now, timezone=tz
            )

        elif schedule.schedule_type == ScheduleType.WEEKLY:
            run = should_run_weekly(
                run_time=schedule.run_time,
                weekdays=schedule.run_time_weekdays,
                current_time=now,
                timezone=tz,
            )

        elif (
            schedule.schedule_type == ScheduleType.MONTHLY
            and schedule.monthly_type == MonthlyType.DAYS
        ):
            run = should_run_monthly(
                run_time=schedule.run_time,
                days=schedule.monthly_days_of_month,
                months=schedule.monthly_months_of_year,
                current_time=schedule.run_time,
                timezone=tz,
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
                current_time=schedule.run_time,
                timezone=tz,
            )

        if run:
            report.locked_at = djangotime.now()
            report.save(update_fields=["locked_at"])
            run_scheduled_report(schedule=report)


@app.task
def email_report(
    template_name: str,
    recipients: List[str] = [],
    report_link: Optional[str] = None,
    attachment: Optional[bytes] = None,
):
    core = get_core_settings()

    subject = f"Scheduled Report: {template_name}"

    # html report
    if report_link:
        body = f"Follow the link to view your report\n\n{report_link}"
    else:
        body = "You PDF report is attached"

    core.send_mail(
        subject=subject,
        body=body,
        attachment=attachment,
        attachment_filename=template_name,
        override_recipients=recipients,
    )
