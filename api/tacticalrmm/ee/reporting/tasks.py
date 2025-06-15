from django.utils import timezone as djangotime
from django.conf import settings
from typing import Optional, List
from tacticalrmm.logger import logger

from tacticalrmm.celery import app
from tacticalrmm.scheduler import should_run_daily, should_run_weekly, should_run_monthly, should_run_monthly_dow
from .models import ReportSchedule
from .utils import generate_html, generate_pdf, normalize_asset_url, create_report_history
from core.models import ScheduleType, MonthlyType
from tacticalrmm.utils import get_default_timezone, get_core_settings
from jinja2.exceptions import TemplateError

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
    tz = get_default_timezone

    reports = ReportSchedule.objects.select_related("report_template", "schedule").filter(enabled=True)

    for report in reports:
        schedule = report.schedule

        run = False

        if (
            schedule.locked_at
            and schedule.locked_at > now - djangotime.timedelta(seconds=55)
        ):
            # prevent race
            logger.error(
                f"Report Schedule for template: {schedule.report_template.name} already executed too recently, skipping."
            )
            continue

        elif schedule.schedule_type == ScheduleType.DAILY:
            run = should_run_daily(run_time=schedule.run_time, current_time=now, timezone=tz)


        elif schedule.schedule_type == ScheduleType.WEEKLY:
            run = should_run_weekly(run_time=schedule.run_time, weekdays=schedule.run_time_weekdays, current_time=now, timezone=tz)

        elif schedule.schedule_type == ScheduleType.MONTHLY and schedule.monthly_type == MonthlyType.DAYS:
            run = should_run_monthly(run_time=schedule.run_time, days=schedule.monthly_days_of_month, months=schedule.monthly_months_of_year, current_time=schedule.run_time, timezone=tz)

        elif schedule.schedule_type == ScheduleType.MONTHLY and schedule.monthly_type == MonthlyType.WEEKS:
            run = should_run_monthly_dow(run_time=schedule.run_time, weekdays=schedule.run_time_weekdays, weeks=schedule.monthly_weeks_of_month, months=schedule.monthly_months_of_year, current_time=schedule.run_time, timezone=tz)

        if run:
            template = report.report_template
            error_text = None
            html_report = ""
            pdf_bytes = None
            report_link = ""

            try:
                html_report, _ = generate_html(
                    template=template.template_md,
                    template_type=template.type,
                    css=template.template_css or "",
                    html_template=(
                        template.template_html.id if template.template_html else None
                    ),
                    variables=template.template_variables,
                    dependencies=report.dependencies,
                )

                html_report = normalize_asset_url(html_report, schedule.format)

            except TemplateError as error:
                if hasattr(error, "lineno"):
                    error_text = f"Line {error.lineno}: {error.message}"
                else:
                    error_text = str(error)
                pass
            except Exception as error:
                error_text = str(error)
                pass

            history = create_report_history(template=template, report_data=html_report, user="system", error_data=error_text)
            
            if not report.no_email:
                if report.format == "pdf":
                    pdf_bytes = generate_pdf(html=html_report)
                else:
                    # build history report link
                    report_link = f"{settings.CORS_ORIGIN_WHITELIST[0]}/reports/history/{history.id}/?format={report.format}"

                email_report.delay(template_name=template.name, report_link=report_link, recipients=schedule.email_recipients, attachment=pdf_bytes)


@app.task
def email_report(template_name:str, recipients: List[str] = [], report_link: Optional[str] = None, attachment: Optional[bytes] = None):
    core = get_core_settings()

    subject = f"Scheduled Report: {template_name}"

    # html report
    if report_link:
        body = f"Follow the link to view your report\n\n{report_link}"
    else:
        body = "You PDF report is attached"

    core.send_mail(subject=subject, body=body, attachment=attachment, attachment_filename=template_name, override_recipients=recipients)