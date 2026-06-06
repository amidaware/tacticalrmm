import asyncio
import logging
import re

import asyncssh
from django.utils import timezone as djangotime

from .audit import (
    _audit_exec_command,
    _audit_session_failed,
    _audit_terminal_command,
    _close_session_and_audit,
    _record_session_and_audit,
)
from .exec import CmdProxy
from .terminal import TerminalProxy

logger = logging.getLogger("trmm")

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][AB012]|\x1b[>=]')


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


class RejectionHandler(asyncssh.SSHServerSession):
    def __init__(self, message, audit_coro=None):
        super().__init__()
        self._message = message
        self._audit_coro = audit_coro
        self._chan = None

    def connection_made(self, chan):
        self._chan = chan
        chan.write(self._message.encode("utf-8", errors="replace"))
        if self._audit_coro:
            asyncio.create_task(self._audit_coro)
        chan.exit(1)

    def eof_received(self):
        return False


class DirectSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, agent, session_id, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint="",
                 gateway_exec_enabled=True, gateway_terminal_enabled=True,
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
        self._gateway_exec_enabled = gateway_exec_enabled
        self._gateway_terminal_enabled = gateway_terminal_enabled
        self._gateway_session_timeout = gateway_session_timeout
        self._gateway_max_sessions = gateway_max_sessions
        self._term = None
        self._exec = None
        self._chan = None
        self._started_at = None
        self._terminal_type = ""
        self._terminal_rows = 0
        self._terminal_cols = 0
        self._session_type = None
        self._exec_cmd = None
        self._exec_completed = False

    def connection_made(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
            logger.info(
                "Gateway session user=%s agent=%s remote_ip=%s client=%s",
                self._user.username, self._agent.agent_id, self._remote_ip, self._client_version,
            )
        except Exception as e:
            logger.error("Gateway connection_made failed: %s", e, exc_info=True)
            raise

    def exec_requested(self, command):
        if not self._gateway_exec_enabled:
            logger.warning("Gateway: exec denied (disabled) user=%s agent=%s from %s",
                           self._user.username, self._agent.agent_id, self._remote_ip)
            audit = _audit_session_failed(
                username=self._user.username, agent_id=self._agent.agent_id,
                remote_ip=self._remote_ip, reason="exec_disabled",
                ssh_key_name=self._ssh_key_name, ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
            return RejectionHandler(
                "SSH gateway exec access is disabled by your administrator.\r\n",
                audit_coro=audit,
            )
        self._session_type = "exec"
        self._exec_cmd = command
        asyncio.create_task(self._start_exec())
        return True

    async def _start_exec(self):
        async def output_cb(data, done=False, exit_code=None):
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                data = _strip_ansi(data).rstrip()
                if data:
                    if not data.endswith('\n'):
                        data += '\n'
                    if self._chan and not self._chan.is_closing():
                        self._chan.write(data)
                if done:
                    self._exec_completed = True
                    asyncio.create_task(_audit_exec_command(
                        self._user, self._agent, self._exec_cmd, exit_code,
                    ))
                    asyncio.create_task(_close_session_and_audit(
                        self._user, self._agent, self._session_id, self._remote_ip,
                        self._started_at,
                    ))
                    if self._chan and not self._chan.is_closing():
                        self._chan.exit(exit_code or 0)
            except Exception:
                logger.error("Gateway exec output_cb error", exc_info=True)

        try:
            self._exec = CmdProxy(self._agent, self._session_id, self._exec_cmd)
            await self._exec.start(output_cb)
        except Exception as e:
            logger.error("Gateway exec start failed: %s", e, exc_info=True)
            try:
                self._chan.write(f"\r\nFailed to execute command: {e}\r\n")
                self._chan.exit(1)
            except Exception:
                pass

    def shell_requested(self):
        if not self._gateway_terminal_enabled:
            logger.warning("Gateway: shell denied (disabled) user=%s agent=%s from %s",
                           self._user.username, self._agent.agent_id, self._remote_ip)
            audit = _audit_session_failed(
                username=self._user.username, agent_id=self._agent.agent_id,
                remote_ip=self._remote_ip, reason="terminal_disabled",
                ssh_key_name=self._ssh_key_name, ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
            return RejectionHandler(
                "SSH gateway terminal access is disabled by your administrator.\r\n",
                audit_coro=audit,
            )
        self._session_type = "shell"
        shell = self._agent.effective_default_shell
        self._term = TerminalProxy(self._agent, self._session_id, shell)
        role_name = "None"
        if self._user.role:
            role_name = self._user.role.name
        os_info = self._agent.operating_system or "Unknown"
        agent_ver = self._agent.version or "Unknown"
        pubip = self._agent.public_ip or "N/A"
        local_ips_val = getattr(self._agent, 'local_ips', None)
        if local_ips_val:
            local_ips = str(local_ips_val)
        else:
            local_ips = "N/A"
        try:
            self._chan.write(
                f"\r\n\x1b[32mWelcome, \x1b[1m{self._user.username}\x1b[0m\x1b[32m [\x1b[1mRole: {role_name}\x1b[0m\x1b[32m]\x1b[0m\r\n"
                f"\x1b[32mSSH session open on \x1b[1m{self._agent.hostname}\x1b[0m\x1b[32m "
                f"({os_info}), shell: {shell}, agent: {agent_ver}, via TRMM proxy\x1b[0m\r\n"
                f"\x1b[32mpubip: {pubip}, local IPs: {local_ips}\x1b[0m\r\n\r\n"
            )
        except Exception as e:
            logger.error("Gateway shell welcome write failed: %s", e)
        asyncio.create_task(self._start_terminal())
        asyncio.create_task(
            _record_session_and_audit(
                self._user, self._agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
        )
        logger.info(
            "Gateway shell started user=%s agent=%s remote_ip=%s client=%s",
            self._user.username, self._agent.agent_id, self._remote_ip, self._client_version,
        )
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
        if not self._gateway_terminal_enabled:
            return False
        self._terminal_type = term_type
        if term_size:
            self._terminal_cols, self._terminal_rows = term_size[0], term_size[1]
        return True

    def terminal_modes(self):
        return {
            asyncssh.VEOF: 4,
            asyncssh.VINTR: 3,
            asyncssh.VKILL: 21,
            asyncssh.VQUIT: 28,
            asyncssh.VSTART: 17,
            asyncssh.VSTOP: 19,
            asyncssh.VSUSP: 26,
            asyncssh.VTIME: 0,
            asyncssh.VMIN: 1,
            asyncssh.ECHO: 0,
            asyncssh.ECHOE: 0,
            asyncssh.ECHOK: 0,
            asyncssh.ECHOKE: 0,
            asyncssh.ECHOCTL: 0,
            asyncssh.ECHOPRT: 0,
            asyncssh.ISIG: 1,
            asyncssh.ICANON: 1,
            asyncssh.IEXTEN: 1,
            asyncssh.CTERMINAL: 0,
        }

    def data_received(self, data, datatype):
        if self._term:
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
                asyncio.create_task(self._term.write(data))
            except Exception as e:
                logger.error("Gateway terminal write error: %s", e)

    def eof_received(self):
        if self._session_type == "exec" and not self._exec_completed:
            return True
        return False

    def connection_lost(self, exc):
        if self._session_type == "exec" and not self._exec_completed:
            return
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if self._exec:
            asyncio.create_task(self._exec.stop())
        if exc:
            logger.error("Gateway connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.create_task(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if self._exec:
            asyncio.create_task(self._exec.stop())
        if self._started_at and self._session_type == "shell":
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
                "Gateway session ended user=%s agent=%s duration=%ds",
                self._user.username, self._agent.agent_id,
                int((djangotime.now() - self._started_at).total_seconds()),
            )