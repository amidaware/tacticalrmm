import datetime as dt
from time import sleep
from typing import Optional

from django.utils import timezone as djangotime

from alerts.models import Alert
from checks.models import CheckResult
from tacticalrmm.celery import app
from tacticalrmm.helpers import rand_range
from tacticalrmm.logger import logger


@app.task
def handle_check_email_alert_task(
    pk: int, alert_interval: Optional[float] = None
) -> str:
    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending email
    if not alert.email_sent:
        check_result = CheckResult.objects.get(
            assigned_check=alert.assigned_check, agent=alert.agent
        )
        sleep(rand_range(100, 1500))
        check_result.send_email()
        alert.email_sent = djangotime.now()
        alert.save(update_fields=["email_sent"])
    else:
        if alert_interval:
            # send an email only if the last email sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.email_sent < delta:
                check_result = CheckResult.objects.get(
                    assigned_check=alert.assigned_check, agent=alert.agent
                )
                sleep(rand_range(100, 1500))
                check_result.send_email()
                alert.email_sent = djangotime.now()
                alert.save(update_fields=["email_sent"])

    return "ok"


@app.task
def handle_check_sms_alert_task(pk: int, alert_interval: Optional[float] = None) -> str:
    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending text
    if not alert.sms_sent:
        check_result = CheckResult.objects.get(
            assigned_check=alert.assigned_check, agent=alert.agent
        )
        sleep(rand_range(100, 1500))
        check_result.send_sms()
        alert.sms_sent = djangotime.now()
        alert.save(update_fields=["sms_sent"])
    else:
        if alert_interval:
            # send a text only if the last text sent is older than 24 hours
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.sms_sent < delta:
                check_result = CheckResult.objects.get(
                    assigned_check=alert.assigned_check, agent=alert.agent
                )
                sleep(rand_range(100, 1500))
                check_result.send_sms()
                alert.sms_sent = djangotime.now()
                alert.save(update_fields=["sms_sent"])

    return "ok"


@app.task
def handle_resolved_check_sms_alert_task(pk: int) -> str:
    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending text
    if not alert.resolved_sms_sent:
        check_result = CheckResult.objects.get(
            assigned_check=alert.assigned_check, agent=alert.agent
        )
        sleep(rand_range(100, 1500))
        check_result.send_resolved_sms()
        alert.resolved_sms_sent = djangotime.now()
        alert.save(update_fields=["resolved_sms_sent"])

    return "ok"


@app.task
def handle_resolved_check_email_alert_task(pk: int) -> str:
    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending email
    if not alert.resolved_email_sent:
        check_result = CheckResult.objects.get(
            assigned_check=alert.assigned_check, agent=alert.agent
        )
        sleep(rand_range(100, 1500))
        check_result.send_resolved_email()
        alert.resolved_email_sent = djangotime.now()
        alert.save(update_fields=["resolved_email_sent"])

    return "ok"


@app.task
def prune_check_history(older_than_days: int) -> str:
    from .models import CheckHistory

    c, _ = CheckHistory.objects.filter(
        x__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()
    logger.info(f"Pruned {c} check history objects")

    return "ok"
