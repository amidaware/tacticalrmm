import datetime as dt
from functools import partial
from time import sleep
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone as djangotime

from agents.models import Agent
from core.utils import get_core_settings
from logs.models import DebugLog
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.constants import (
    AGENT_DEFER,
    AGENT_OUTAGES_LOCK,
    AGENT_STATUS_OVERDUE,
    FILE_TRANSFER_IDLE_EXPIRE_MINUTES,
    FILE_TRANSFER_SESSION_RETENTION_HOURS,
    CheckStatus,
    DebugLogType,
    FileTransferOperation,
    FileTransferStatus,
)
from tacticalrmm.helpers import rand_range
from tacticalrmm.logger import logger
from tacticalrmm.utils import redis_lock

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


@app.task
def send_agent_update_task(*, agent_ids: list[str], token: str, force: bool) -> None:
    agents: "QuerySet[Agent]" = Agent.objects.defer(*AGENT_DEFER).filter(
        agent_id__in=agent_ids
    )
    for agent in agents:
        agent.do_update(token=token, force=force)


@app.task
def auto_self_agent_update_task() -> None:
    if getattr(settings, "TRMM_DISABLE_AGENT_AUTO_UPDATE_TASK", False):
        return

    call_command("update_agents")


@app.task
def agent_outage_email_task(pk: int, alert_interval: Optional[float] = None) -> str:
    from alerts.models import Alert

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    if not alert.email_sent:
        sleep(rand_range(100, 1500))
        alert.agent.send_outage_email()
        alert.email_sent = djangotime.now()
        alert.save(update_fields=["email_sent"])
    else:
        if alert_interval:
            # send an email only if the last email sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.email_sent < delta:
                sleep(rand_range(100, 1500))
                alert.agent.send_outage_email()
                alert.email_sent = djangotime.now()
                alert.save(update_fields=["email_sent"])

    return "ok"


@app.task
def agent_recovery_email_task(pk: int) -> str:
    from alerts.models import Alert

    sleep(rand_range(100, 1500))

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    alert.agent.send_recovery_email()
    alert.resolved_email_sent = djangotime.now()
    alert.save(update_fields=["resolved_email_sent"])

    return "ok"


@app.task
def agent_outage_sms_task(pk: int, alert_interval: Optional[float] = None) -> str:
    from alerts.models import Alert

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    if not alert.sms_sent:
        sleep(rand_range(100, 1500))
        alert.agent.send_outage_sms()
        alert.sms_sent = djangotime.now()
        alert.save(update_fields=["sms_sent"])
    else:
        if alert_interval:
            # send an sms only if the last sms sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.sms_sent < delta:
                sleep(rand_range(100, 1500))
                alert.agent.send_outage_sms()
                alert.sms_sent = djangotime.now()
                alert.save(update_fields=["sms_sent"])

    return "ok"


@app.task
def agent_recovery_sms_task(pk: int) -> str:
    from alerts.models import Alert

    sleep(rand_range(100, 1500))
    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    alert.agent.send_recovery_sms()
    alert.resolved_sms_sent = djangotime.now()
    alert.save(update_fields=["resolved_sms_sent"])

    return "ok"


@app.task(bind=True)
def agent_outages_task(self) -> str:
    with redis_lock(AGENT_OUTAGES_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

        from alerts.models import Alert
        from core.tasks import _get_agent_qs

        for agent in _get_agent_qs():
            if agent.status == AGENT_STATUS_OVERDUE:
                Alert.handle_alert_failure(agent)

        return "completed"


@app.task
def run_script_email_results_task(
    agentpk: int,
    scriptpk: int,
    nats_timeout: int,
    emails: list[str],
    args: list[str] = [],
    history_pk: int = 0,
    run_as_user: bool = False,
    env_vars: list[str] = [],
):
    agent = Agent.objects.get(pk=agentpk)
    script = Script.objects.get(pk=scriptpk)
    r = agent.run_script(
        scriptpk=script.pk,
        args=args,
        full=True,
        timeout=nats_timeout,
        wait=True,
        history_pk=history_pk,
        run_as_user=run_as_user,
        env_vars=env_vars,
    )
    if r == "timeout":
        DebugLog.error(
            agent=agent,
            log_type=DebugLogType.SCRIPTING,
            message=f"{agent.hostname}({agent.pk}) timed out running script.",
        )
        return

    CORE = get_core_settings()
    subject = f"{agent.client.name}, {agent.site.name}, {agent.hostname} {script.name} Results"
    exec_time = "{:.4f}".format(r["execution_time"])
    body = (
        subject
        + f"\nReturn code: {r['retcode']}\nExecution time: {exec_time} seconds\nStdout: {r['stdout']}\nStderr: {r['stderr']}"
    )

    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = CORE.smtp_from_email

    if emails:
        msg["To"] = ", ".join(emails)
    else:
        msg["To"] = ", ".join(CORE.email_alert_recipients)

    msg.set_content(body)

    try:
        with smtplib.SMTP(CORE.smtp_host, CORE.smtp_port, timeout=20) as server:
            if CORE.smtp_requires_auth:
                server.ehlo()
                server.starttls()
                server.login(CORE.smtp_host_user, CORE.smtp_host_password)
                server.send_message(msg)
                server.quit()
            else:
                server.send_message(msg)
                server.quit()
    except Exception as e:
        DebugLog.error(message=str(e))


@app.task
def clear_faults_task(older_than_days: int) -> None:
    from alerts.models import Alert

    # https://github.com/amidaware/tacticalrmm/issues/484
    agents = Agent.objects.exclude(last_seen__isnull=True).filter(
        last_seen__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    )
    for agent in agents:
        for check in agent.get_checks_with_policies():
            # reset check status
            if check.check_result:
                check.check_result.status = CheckStatus.PASSING
                check.check_result.save(update_fields=["status"])
            if check.alert.filter(agent=agent, resolved=False).exists():
                alert = Alert.create_or_return_check_alert(check, agent=agent)
                if alert:
                    alert.resolve()

        # reset overdue alerts
        agent.overdue_email_alert = False
        agent.overdue_text_alert = False
        agent.overdue_dashboard_alert = False
        agent.save(
            update_fields=[
                "overdue_email_alert",
                "overdue_text_alert",
                "overdue_dashboard_alert",
            ]
        )


@app.task
def prune_agent_history(older_than_days: int) -> str:
    from .models import AgentHistory

    AgentHistory.objects.filter(
        time__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    ).delete()

    return "ok"


_FILE_TRANSFER_ACTIVE_STATUSES = (
    FileTransferStatus.WAITING_FOR_AGENT,
    FileTransferStatus.AGENT_READY,
    FileTransferStatus.TRANSFERRING,
)


EXTRACT_EXPIRED_MESSAGE = (
    "The agent stopped responding (it may have gone offline or restarted)."
)


def expire_stale_file_transfer_sessions(
    *, agent=None, notify_agent: bool = True
) -> int:
    from agents.utils import send_nats_command

    from .file_transfer_relay import (
        clear_download_session_redis,
        clear_upload_session_redis,
        get_download_ack,
        get_upload_ack,
    )
    from .models import FileTransferSession

    def _clear_redis(session: "FileTransferSession") -> None:
        if session.operation == FileTransferOperation.EXTRACT:
            return
        if session.operation == FileTransferOperation.UPLOAD:
            clear_upload_session_redis(session.session_id)
        else:
            clear_download_session_redis(session.session_id)

    def _notify_agent_release(session: "FileTransferSession") -> None:
        agent_obj = session.agent
        if agent_obj is None or agent_obj.status != "online":
            return
        try:
            if session.operation == FileTransferOperation.EXTRACT:
                send_nats_command(
                    agent_obj,
                    "files_extract_cancel",
                    {"session_id": str(session.session_id)},
                    timeout=5,
                )
            elif session.operation == FileTransferOperation.UPLOAD:
                send_nats_command(
                    agent_obj,
                    "files_upload_abort",
                    {"session_id": str(session.session_id)},
                    timeout=5,
                )
            else:
                send_nats_command(
                    agent_obj,
                    "files_download_finalize",
                    {
                        "session_id": str(session.session_id),
                        "source_path": session.destination_path,
                        "release": "true",
                    },
                    timeout=5,
                )
        except Exception:
            pass

    def _live_committed(session: "FileTransferSession") -> int:
        if session.operation == FileTransferOperation.EXTRACT:
            return session.committed_offset
        if session.operation == FileTransferOperation.UPLOAD:
            redis_committed = get_upload_ack(session.session_id)
        else:
            redis_committed = get_download_ack(session.session_id)
        return max(session.committed_offset, redis_committed or 0)

    def _should_idle_expire(session: "FileTransferSession", idle_cutoff) -> bool:
        if max(session.created_at, session.updated_at) > idle_cutoff:
            return False
        if session.last_ack_at is not None or session.committed_offset > 0:
            return False
        if (
            session.is_archive
            and session.status == FileTransferStatus.WAITING_FOR_AGENT
        ):
            return False
        try:
            return _live_committed(session) <= 0
        except Exception:
            return False

    now = djangotime.now()
    idle_cutoff = now - dt.timedelta(minutes=FILE_TRANSFER_IDLE_EXPIRE_MINUTES)
    qs = FileTransferSession.objects.filter(
        status__in=_FILE_TRANSFER_ACTIVE_STATUSES,
    ).select_related("agent")
    if agent is not None:
        qs = qs.filter(agent=agent)

    def _release(session: "FileTransferSession") -> None:
        _clear_redis(session)
        _notify_agent_release(session)

    expired_count = 0
    for session in qs.iterator():
        ttl_expired = session.expires_at <= now
        idle_expired = _should_idle_expire(session, idle_cutoff)
        if not ttl_expired and not idle_expired:
            continue
        with transaction.atomic():
            # a complete or cancel may have finished it since the query
            locked = (
                FileTransferSession.objects.select_for_update()
                .filter(pk=session.pk, status__in=_FILE_TRANSFER_ACTIVE_STATUSES)
                .first()
            )
            if locked is None:
                continue
            locked.status = FileTransferStatus.EXPIRED
            if locked.operation == FileTransferOperation.EXTRACT:
                locked.error_message = locked.error_message or EXTRACT_EXPIRED_MESSAGE
            locked.error_message = locked.error_message or (
                "Session expired after 10 minutes with no data transferred"
                if idle_expired and not ttl_expired
                else "Session expired"
            )
            locked.save(update_fields=["status", "error_message", "updated_at"])
        locked.agent = session.agent
        session = locked
        if notify_agent:
            _release(session)
        else:
            transaction.on_commit(partial(_release, session))
        logger.error(
            "file_transfer session=%s operation=%s status=%s: %s",
            session.session_id,
            session.operation,
            session.status,
            session.error_message,
        )
        expired_count += 1

    if notify_agent:
        leftover_expired = FileTransferSession.objects.filter(
            status=FileTransferStatus.EXPIRED,
            error_message="",
        ).select_related("agent")
        if agent is not None:
            leftover_expired = leftover_expired.filter(agent=agent)
        for session in leftover_expired.iterator():
            _clear_redis(session)
            _notify_agent_release(session)
            session.error_message = "Session expired"
            session.save(update_fields=["error_message", "updated_at"])
            logger.error(
                "file_transfer session=%s operation=%s status=%s: %s",
                session.session_id,
                session.operation,
                session.status,
                session.error_message,
            )
            expired_count += 1
    return expired_count


@app.task
def cleanup_expired_file_transfers_task() -> str:
    from .models import FileTransferSession

    expired_count = expire_stale_file_transfer_sessions()

    now = djangotime.now()
    retention_cutoff = now - dt.timedelta(hours=FILE_TRANSFER_SESSION_RETENTION_HOURS)
    old_terminal = FileTransferSession.objects.filter(
        status__in=(
            FileTransferStatus.COMPLETED,
            FileTransferStatus.FAILED,
            FileTransferStatus.EXPIRED,
            FileTransferStatus.CANCELLED,
        ),
        updated_at__lt=retention_cutoff,
    )
    deleted_count, _ = old_terminal.delete()

    return f"expired={expired_count} deleted={deleted_count}"


@app.task
def bulk_recover_agents_task() -> None:
    call_command("bulk_restart_agents")
