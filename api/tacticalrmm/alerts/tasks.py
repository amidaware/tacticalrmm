from django.utils import timezone as djangotime

from tacticalrmm.celery import app

from alerts.models import Alert


@app.task
def unsnooze_alerts() -> str:

    Alert.objects.filter(snoozed=True, snooze_until__lte=djangotime.now()).update(
        snoozed=False, snooze_until=None
    )

    return "ok"


@app.task
def periodic_alert_notifications() -> str:
    return "not implemented"