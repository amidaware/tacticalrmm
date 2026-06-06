import logging

from asgiref.sync import sync_to_async
from django.utils import timezone as djangotime

from logs.models import AuditLog

logger = logging.getLogger("trmm")


@sync_to_async
def _record_session_and_audit(
    user, agent, session_id, remote_ip, client_version="",
    ssh_key_name="", ssh_key_type="", ssh_key_fingerprint="",
):
    from accounts.models import SSHSession
    now = djangotime.now()
    SSHSession.objects.create(
        user=user, agent=agent, session_id=session_id,
        remote_ip=remote_ip, started_at=now,
        client_version=client_version,
    )
    AuditLog.audit_ssh_session_start(
        username=user.username, agent=agent, session_id=session_id,
        remote_ip=remote_ip, client_version=client_version,
        ssh_key_name=ssh_key_name, ssh_key_type=ssh_key_type,
        ssh_key_fingerprint=ssh_key_fingerprint,
    )


@sync_to_async
def _close_session_and_audit(
    user, agent, session_id, remote_ip, started_at,
    terminal_type="", terminal_rows=0, terminal_cols=0,
):
    from accounts.models import SSHSession
    now = djangotime.now()
    duration = int((now - started_at).total_seconds())
    SSHSession.objects.filter(session_id=session_id).update(closed_at=now)
    AuditLog.audit_ssh_session_end(
        username=user.username, agent=agent, session_id=session_id,
        remote_ip=remote_ip, started_at=str(started_at),
        closed_at=str(now), duration=duration,
        terminal_type=terminal_type, terminal_rows=terminal_rows,
        terminal_cols=terminal_cols,
    )


@sync_to_async
def _audit_exec_command(user, agent, command, exit_code=None):
    try:
        AuditLog.audit_raw_command(
            username=user.username,
            agent=agent,
            cmd=command,
            shell="ssh",
        )
        logger.info(
            "Gateway exec user=%s agent=%s cmd=%s exit=%s",
            user.username, agent.agent_id, command, exit_code,
        )
    except Exception:
        logger.error("Gateway exec audit failed", exc_info=True)


@sync_to_async
def _audit_terminal_command(user, agent, command):
    try:
        AuditLog.audit_raw_command(
            username=user.username,
            agent=agent,
            cmd=command,
            shell="terminal",
        )
    except Exception:
        pass


@sync_to_async
def _audit_session_failed(
    username, agent_id, remote_ip, reason,
    ssh_key_name="", ssh_key_type="", ssh_key_fingerprint="",
):
    AuditLog.audit_ssh_session_failed(
        username=username, agent_id=agent_id, remote_ip=remote_ip,
        reason=reason, ssh_key_name=ssh_key_name,
        ssh_key_type=ssh_key_type, ssh_key_fingerprint=ssh_key_fingerprint,
    )
