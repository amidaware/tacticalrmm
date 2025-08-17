from django.utils import timezone as djangotime

from agents.models import Agent
from tacticalrmm.celery import app

from .models import Alert


@app.task
def unsnooze_alerts() -> str:
    Alert.objects.filter(snoozed=True, snooze_until__lte=djangotime.now()).update(
        snoozed=False, snooze_until=None
    )

    return "ok"


@app.task
def cache_agents_alert_template() -> str:
    for agent in Agent.objects.only(
        "pk", "site", "policy", "alert_template"
    ).select_related("site", "policy", "alert_template"):
        agent.set_alert_template()

    return "ok"


@app.task
def prune_resolved_alerts(older_than_days: int) -> str:
    Alert.objects.filter(resolved=True).filter(
        alert_time__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"
