import asyncio
import logging
import re

import asyncssh
from django.utils import timezone as djangotime

from .constants import ANSI_ESCAPE, TERMINAL_MODES, WELCOME_TEMPLATE
from .audit import (
    _audit_terminal_command,
    _close_session_and_audit,
    _record_session_and_audit,
)

logger = logging.getLogger("trmm")


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


class DataBuffer:
    def __init__(self):
        self._buf = b""

    def append(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8", errors="replace")
        self._buf += data

    def has_line(self):
        return b"\r" in self._buf or b"\n" in self._buf

    def split_lines(self):
        lines = self._buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
        self._buf = lines.pop()
        return [line for line in lines if line.strip() and not any(b < 32 for b in line if b not in (9,))]


def build_welcome_message(username, role_name, hostname, os_info, shell, agent_ver, pubip, local_ips):
    return WELCOME_TEMPLATE.format(
        username=username,
        role=role_name or "None",
        hostname=hostname,
        os_info=os_info,
        shell=shell,
        agent_ver=agent_ver,
        pubip=pubip,
        local_ips=local_ips,
    )


def get_local_ips(agent):
    local_ips_val = getattr(agent, 'local_ips', None)
    if local_ips_val:
        return str(local_ips_val)
    return "N/A"


class BaseSessionMixin:
    _user = None
    _agent = None
    _session_id = None
    _remote_ip = None
    _client_version = ""
    _ssh_key_name = ""
    _ssh_key_type = ""
    _ssh_key_fingerprint = ""
    _started_at = None
    _chan = None
    _term_buf = None

    def _setup_connection(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
        except Exception as e:
            logger.error("Gateway connection setup failed: %s", e, exc_info=True)

    def _write_welcome(self, shell):
        role_name = self._user.role.name if self._user.role else None
        os_info = self._agent.operating_system or "Unknown"
        agent_ver = self._agent.version or "Unknown"
        pubip = self._agent.public_ip or "N/A"
        local_ips = get_local_ips(self._agent)
        msg = build_welcome_message(
            self._user.username,
            role_name,
            self._agent.hostname,
            os_info,
            shell,
            agent_ver,
            pubip,
            local_ips,
        )
        try:
            self._chan.write(msg)
        except Exception as e:
            logger.error("Gateway welcome write failed: %s", e)

    def _record_session(self):
        return _record_session_and_audit(
            self._user, self._agent, self._session_id, self._remote_ip,
            client_version=self._client_version,
            ssh_key_name=self._ssh_key_name,
            ssh_key_type=self._ssh_key_type,
            ssh_key_fingerprint=self._ssh_key_fingerprint,
        )

    def _close_session(self, terminal_type="", rows=0, cols=0):
        return _close_session_and_audit(
            self._user, self._agent, self._session_id, self._remote_ip,
            self._started_at,
            terminal_type=terminal_type,
            terminal_rows=rows,
            terminal_cols=cols,
        )

    def _audit_terminal_input(self, line):
        return _audit_terminal_command(self._user, self._agent, line)

    def _safe_write(self, data):
        if self._chan and not self._chan.is_closing():
            self._chan.write(data)

    def _safe_exit(self, code=0):
        if self._chan and not self._chan.is_closing():
            self._chan.exit(code)