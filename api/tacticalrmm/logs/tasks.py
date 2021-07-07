from django.utils import timezone as djangotime
import datetime as dt

from tacticalrmm.celery import app


@app.task
def prune_debug_log(older_than_days: int) -> str:
    from .models import DebugLog

    DebugLog.objects.filter(
        x__lt=djangotime.make_aware(dt.datetime.today())
        - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"