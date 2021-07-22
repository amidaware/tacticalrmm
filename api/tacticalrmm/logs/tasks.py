from django.utils import timezone as djangotime

from tacticalrmm.celery import app


@app.task
def prune_debug_log(older_than_days: int) -> str:
    from .models import DebugLog

    DebugLog.objects.filter(
        entry_time__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"


@app.task
def prune_audit_log(older_than_days: int) -> str:
    from .models import AuditLog

    AuditLog.objects.filter(
        entry_time__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"
