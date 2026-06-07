import asyncio
import logging

import asyncssh
from django.utils import timezone as djangotime

from .audit import (
    _audit_terminal_command,
    _close_session_and_audit,
    _record_session_and_audit,
)
from .constants import ANSI_ESCAPE, TERMINAL_MODES, get_local_ips, build_welcome_message
from .direct_terminal import TerminalProxy

logger = logging.getLogger("trmm")


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


async def start_terminal_session(chan, user, agent, session_id, remote_ip,
                                  client_version="", ssh_key_name="",
                                  ssh_key_type="", ssh_key_fingerprint=""):
    shell = agent.effective_default_shell
    term = TerminalProxy(agent, session_id, shell)

    role_name = user.role.name if user.role else None
    os_info = agent.operating_system or "Unknown"
    agent_ver = agent.version or "Unknown"
    pubip = agent.public_ip or "N/A"
    local_ips = get_local_ips(agent)

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

    asyncio.create_task(_run_terminal(term, chan, user, agent, session_id, remote_ip, started_at=djangotime.now()))


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


class TerminalSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, agent, session_id, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint="",
                 gateway_session_timeout=300, gateway_max_sessions=10):
        super().__init__()
        self._user = user
        self._agent = agent
        self._session_id = session_id
        self._remote_ip = remote_ip
        self._client_version = client_version
        self._ssh_key_name = ssh_key_name
        self._ssh_key_type = ssh_key_type
        self._ssh_key_fingerprint = ssh_key_fingerprint
        self._gateway_session_timeout = gateway_session_timeout
        self._gateway_max_sessions = gateway_max_sessions
        self._term = None
        self._chan = None
        self._started_at = None
        self._terminal_type = ""
        self._terminal_rows = 0
        self._terminal_cols = 0

    def connection_made(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
            logger.info(
                "Gateway terminal session user=%s agent=%s remote_ip=%s client=%s",
                self._user.username, self._agent.agent_id, self._remote_ip, self._client_version,
            )
        except Exception as e:
            logger.error("Gateway terminal connection_made failed: %s", e, exc_info=True)
            raise

    def shell_requested(self):
        self._session_type = "shell"
        shell = self._agent.effective_default_shell
        self._term = TerminalProxy(self._agent, self._session_id, shell)

        role_name = self._user.role.name if self._user.role else None
        os_info = self._agent.operating_system or "Unknown"
        agent_ver = self._agent.version or "Unknown"
        pubip = self._agent.public_ip or "N/A"
        local_ips = get_local_ips(self._agent)

        msg = build_welcome_message(
            self._user.username, role_name, self._agent.hostname,
            os_info, shell, agent_ver, pubip, local_ips,
        )
        try:
            self._chan.write(msg)
        except Exception as e:
            logger.error("Gateway terminal welcome write failed: %s", e)

        asyncio.create_task(_record_session_and_audit(
            self._user, self._agent, self._session_id, self._remote_ip,
            client_version=self._client_version,
            ssh_key_name=self._ssh_key_name,
            ssh_key_type=self._ssh_key_type,
            ssh_key_fingerprint=self._ssh_key_fingerprint,
        ))
        asyncio.create_task(self._start_terminal())
        return True

    async def _start_terminal(self):
        async def output_cb(data, done=False, exit_code=None):
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                data = _strip_ansi(data)
                if data and self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                if done:
                    asyncio.create_task(_close_session_and_audit(
                        self._user, self._agent, self._session_id, self._remote_ip,
                        self._started_at,
                        terminal_type=self._terminal_type,
                        terminal_rows=self._terminal_rows,
                        terminal_cols=self._terminal_cols,
                    ))
                    if self._chan and not self._chan.is_closing():
                        self._chan.exit(exit_code or 0)
            except Exception as e:
                logger.error("Gateway terminal output_cb error: %s", e)

        try:
            await self._term.start(output_cb)
        except Exception as e:
            logger.error("Gateway terminal start failed: %s", e, exc_info=True)
            try:
                self._chan.write(f"\r\nFailed to start terminal: {e}\r\n")
                self._chan.exit(1)
            except Exception:
                pass

    def pty_requested(self, term_type, term_size, term_modes):
        self._terminal_type = term_type
        if term_size:
            self._terminal_cols, self._terminal_rows = term_size[0], term_size[1]
        return True

    def terminal_modes(self):
        return TERMINAL_MODES

    def data_received(self, data, datatype):
        if self._term:
            original_data = data
            if isinstance(data, str):
                data = data.encode("utf-8", errors="replace")
            self._term_buf = getattr(self, "_term_buf", b"") + data
            if b"\r" in self._term_buf or b"\n" in self._term_buf:
                lines = self._term_buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
                self._term_buf = lines.pop()
                for line in lines:
                    if line.strip() and not any(b < 32 for b in line if b not in (9,)):
                        asyncio.create_task(_audit_terminal_command(
                            self._user, self._agent, line.decode("utf-8", errors="replace"),
                        ))
            try:
                asyncio.create_task(self._term.write(original_data))
            except Exception as e:
                logger.error("Gateway terminal write error: %s", e)

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if exc:
            logger.error("Gateway terminal connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.create_task(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if self._started_at:
            asyncio.create_task(
                _close_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip,
                    self._started_at,
                    terminal_type=self._terminal_type,
                    terminal_rows=self._terminal_rows,
                    terminal_cols=self._terminal_cols,
                )
            )
            logger.info(
                "Gateway terminal session ended user=%s agent=%s duration=%ds",
                self._user.username, self._agent.agent_id,
                int((djangotime.now() - self._started_at).total_seconds()),
            )