import datetime as dt
import random
from time import sleep
from typing import Union

from tacticalrmm.celery import app
from django.utils import timezone as djangotime


@app.task
def handle_check_email_alert_task(pk, alert_interval: Union[float, None]) -> str:
    from .models import Check

    check = Check.objects.get(pk=pk)

    if not check.agent.maintenance_mode:
        # first time sending email
        if not check.email_sent:
            sleep(random.randint(1, 10))
            check.send_email()
            check.email_sent = djangotime.now()
            check.save(update_fields=["email_sent"])
        else:
            if alert_interval:
                # send an email only if the last email sent is older than alert interval
                delta = djangotime.now() - dt.timedelta(days=alert_interval)
                if check.email_sent < delta:
                    sleep(random.randint(1, 10))
                    check.send_email()
                    check.email_sent = djangotime.now()
                    check.save(update_fields=["email_sent"])

    return "ok"


@app.task
def handle_check_sms_alert_task(pk, alert_interval: Union[float, None]) -> str:
    from .models import Check

    check = Check.objects.get(pk=pk)

    if not check.agent.maintenance_mode:
        # first time sending text
        if not check.text_sent:
            sleep(random.randint(1, 3))
            check.send_sms()
            check.text_sent = djangotime.now()
            check.save(update_fields=["text_sent"])
        else:
            if alert_interval:
                # send a text only if the last text sent is older than 24 hours
                delta = djangotime.now() - dt.timedelta(days=alert_interval)
                if check.text_sent < delta:
                    sleep(random.randint(1, 3))
                    check.send_sms()
                    check.text_sent = djangotime.now()
                    check.save(update_fields=["text_sent"])

    return "ok"


@app.task
def handle_resolved_check_sms_alert_task(pk: int) -> str:
    from .models import Check

    check = Check.objects.get(pk=pk)

    if not check.agent.maintenance_mode:
        # first time sending text
        if not check.resolved_text_sent:
            sleep(random.randint(1, 3))
            check.send_resolved_sms()
            check.resolved_text_sent = djangotime.now()
            check.save(update_fields=["resolved_text_sent"])

    return "ok"


@app.task
def handle_resolved_check_email_alert_task(pk: int) -> str:
    from .models import Check

    check = Check.objects.get(pk=pk)

    if not check.agent.maintenance_mode:
        # first time sending email
        if not check.resolved_email_sent:
            sleep(random.randint(1, 10))
            check.send_resolved_email()
            check.resolved_email_sent = djangotime.now()
            check.save(update_fields=["resolved_email_sent"])

    return "ok"


@app.task
def prune_check_history(older_than_days: int) -> str:
    from .models import CheckHistory

    CheckHistory.objects.filter(
        x__lt=djangotime.make_aware(dt.datetime.today())
        - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"
