import asyncio
import logging

from django.utils import timezone as djangotime

from .constants import ANSI_ESCAPE, TERMINAL_MODES, get_local_ips, build_welcome_message
from .audit import (
    _audit_terminal_command,
    _close_session_and_audit,
    _record_session_and_audit,
)
from .terminal import TerminalProxy

logger = logging.getLogger("trmm")


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


async def start_terminal_session(chan, user, agent, session_id, remote_ip,
                                  client_version="", ssh_key_name="",
                                  ssh_key_type="", ssh_key_fingerprint="",
                                  term=None, terminal_type="",
                                  terminal_rows=0, terminal_cols=0):
    if term is None:
        shell = agent.effective_default_shell
        term = TerminalProxy(agent, session_id, shell)

    role_name = user.role.name if user.role else None
    os_info = agent.operating_system or "Unknown"
    agent_ver = agent.version or "Unknown"
    pubip = agent.public_ip or "N/A"
    local_ips = get_local_ips(agent)
    shell = agent.effective_default_shell

    msg = build_welcome_message(
        user.username, role_name, agent.hostname,
        os_info, shell, agent_ver, pubip, local_ips,
    )
    try:
        chan.write(msg)
    except Exception as e:
        logger.error("Gateway terminal welcome write failed: %s", e)

    asyncio.create_task(_record_session_and_audit(
        user, agent, session_id, remote_ip,
        client_version=client_version,
        ssh_key_name=ssh_key_name,
        ssh_key_type=ssh_key_type,
        ssh_key_fingerprint=ssh_key_fingerprint,
    ))

    started_at = djangotime.now()
    asyncio.create_task(_run_terminal(
        term, chan, user, agent, session_id, remote_ip, started_at=started_at,
        terminal_type=terminal_type, terminal_rows=terminal_rows, terminal_cols=terminal_cols,
    ))


async def _run_terminal(term, chan, user, agent, session_id, remote_ip, started_at,
                        terminal_type="", terminal_rows=0, terminal_cols=0):
    async def output_cb(data, done=False, exit_code=None):
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            data = _strip_ansi(data)
            if data and chan and not chan.is_closing():
                chan.write(data)
            if done:
                asyncio.create_task(_close_session_and_audit(
                    user, agent, session_id, remote_ip, started_at,
                    terminal_type=terminal_type,
                    terminal_rows=terminal_rows,
                    terminal_cols=terminal_cols,
                ))
                if chan and not chan.is_closing():
                    chan.exit(exit_code or 0)
        except Exception as e:
            logger.error("Gateway terminal output_cb error: %s", e)

    try:
        await term.start(output_cb)
    except Exception as e:
        logger.error("Gateway terminal start failed: %s", e, exc_info=True)
        try:
            chan.write(f"\r\nFailed to start terminal: {e}\r\n")
            chan.exit(1)
        except Exception:
            pass


async def write_to_channel(chan, data):
    if data and chan and not chan.is_closing():
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        data = _strip_ansi(data)
        chan.write(data)


async def close_channel(chan, exit_code=0):
    if chan and not chan.is_closing():
        chan.exit(exit_code)