import datetime as dt
import random
from time import sleep

from tacticalrmm.celery import app
from django.utils import timezone as djangotime

from agents.models import Agent


@app.task
def handle_check_email_alert_task(pk):
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
            # send an email only if the last email sent is older than 24 hours
            delta = djangotime.now() - dt.timedelta(hours=24)
            if check.email_sent < delta:
                sleep(random.randint(1, 10))
                check.send_email()
                check.email_sent = djangotime.now()
                check.save(update_fields=["email_sent"])

    return "ok"


@app.task
def handle_check_sms_alert_task(pk):
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
            # send a text only if the last text sent is older than 24 hours
            delta = djangotime.now() - dt.timedelta(hours=24)
            if check.text_sent < delta:
                sleep(random.randint(1, 3))
                check.send_sms()
                check.text_sent = djangotime.now()
                check.save(update_fields=["text_sent"])

    return "ok"


@app.task
def prune_check_history(older_than_days):
    from .models import CheckHistory

    CheckHistory.objects.filter(
        x__lt=djangotime.make_aware(dt.datetime.today())
        - djangotime.timedelta(days=older_than_days)
    ).delete()
