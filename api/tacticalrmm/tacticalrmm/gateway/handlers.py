import asyncio

import asyncssh
from django.utils import timezone as djangotime

from .audit import _audit_session_failed, _audit_exec_command, _audit_terminal_command, _close_session_and_audit, _record_session_and_audit
from .constants import ANSI_ESCAPE, TERMINAL_MODES, _strip_ansi
from .error import (
    DENIED_EXEC_DISABLED,
    DENIED_TERMINAL_DISABLED,
    LOG_EXEC_DISABLED,
    LOG_TERMINAL_DISABLED,
    REASON_EXEC_DISABLED,
    REASON_TERMINAL_DISABLED,
)
from .exec import CmdProxy
from .logger import gw_log
from .terminal import TerminalProxy, start_terminal_session


class RejectionHandler(asyncssh.SSHServerSession):
    def __init__(self, message, audit_coro=None):
        super().__init__()
        self._message = message
        self._audit_coro = audit_coro
        self._chan = None

    def connection_made(self, chan):
        self._chan = chan
        try:
            self._chan.write(self._message.encode() if isinstance(self._message, str) else self._message)
            gw_log.debug("RejectionHandler: wrote denial to channel")
        except Exception as e:
            gw_log.debug("RejectionHandler: write failed: %s", e)
        if self._audit_coro:
            asyncio.create_task(self._audit_coro)
        chan.exit(1)

    def pty_requested(self, term_type, term_size, term_modes):
        return False

    def shell_requested(self):
        return True

    def exec_requested(self, command):
        return True

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        pass

    def closed(self):
        pass


def deny(message, reason=None, audit_user=None, audit_agent_id=None,
         audit_remote_ip=None, ssh_key_name="", ssh_key_type="",
         ssh_key_fingerprint=""):
    audit_coro = None
    if reason:
        audit_coro = _audit_session_failed(
            username=audit_user or "",
            agent_id=audit_agent_id or "",
            remote_ip=audit_remote_ip or "",
            reason=reason,
            ssh_key_name=ssh_key_name,
            ssh_key_type=ssh_key_type,
            ssh_key_fingerprint=ssh_key_fingerprint,
        )
    return RejectionHandler(message, audit_coro=audit_coro)


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
        self._chan = None
        self._started_at = None
        self._session_type = None
        self._terminal_type = ""
        self._terminal_rows = 0
        self._terminal_cols = 0
        self._exec_cmd = None
        self._exec_completed = False

    def connection_made(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
            gw_log.info(
                "Gateway session user=%s agent=%s remote_ip=%s client=%s",
                self._user.username, self._agent.agent_id, self._remote_ip, self._client_version,
            )
        except Exception as e:
            gw_log.error("Gateway connection_made failed: %s", e, exc_info=True)
            raise

    def exec_requested(self, command):
        if not self._gateway_exec_enabled:
            gw_log.warning(LOG_EXEC_DISABLED,
                           self._user.username, self._agent.agent_id, self._remote_ip)
            return deny(
                DENIED_EXEC_DISABLED, reason=REASON_EXEC_DISABLED,
                audit_user=self._user.username, audit_agent_id=self._agent.agent_id,
                audit_remote_ip=self._remote_ip,
                ssh_key_name=self._ssh_key_name, ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
        self._exec_cmd = command
        self._session_type = "exec"
        asyncio.create_task(self._start_exec())
        return True

    async def _start_exec(self):
        from .exec import run_exec

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
                gw_log.error("Gateway exec output_cb error", exc_info=True)

        try:
            await run_exec(self._user, self._agent, self._session_id, self._exec_cmd, output_cb)
        except Exception as e:
            gw_log.error("Gateway exec start failed: %s", e, exc_info=True)
            try:
                self._chan.write(f"\r\nFailed to execute command: {e}\r\n")
                self._chan.exit(1)
            except Exception:
                pass

    def pty_requested(self, term_type, term_size, term_modes):
        if not self._gateway_terminal_enabled:
            asyncio.create_task(_audit_session_failed(
                username=self._user.username, agent_id=self._agent.agent_id,
                remote_ip=self._remote_ip, reason=REASON_TERMINAL_DISABLED,
                ssh_key_name=self._ssh_key_name, ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            ))
            return False
        self._terminal_type = term_type
        if term_size:
            self._terminal_cols, self._terminal_rows = term_size[0], term_size[1]
        self._session_type = "shell"
        return True

    def terminal_modes(self):
        return TERMINAL_MODES

    def shell_requested(self):
        if not self._gateway_terminal_enabled:
            return RejectionHandler(
                "SSH gateway terminal access is disabled by your administrator.\r\n",
            )
        self._session_type = "shell"
        asyncio.create_task(self._start_terminal())
        return True

    async def _start_terminal(self):
        from .terminal import start_terminal_session

        try:
            shell = self._agent.effective_default_shell
            self._term = TerminalProxy(self._agent, self._session_id, shell)
            asyncio.create_task(start_terminal_session(
                self._chan, self._user, self._agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
                term=self._term,
                terminal_type=self._terminal_type,
                terminal_rows=self._terminal_rows,
                terminal_cols=self._terminal_cols,
            ))
        except Exception as e:
            gw_log.error("Gateway terminal start failed: %s", e, exc_info=True)
            try:
                self._chan.write(f"\r\nFailed to start terminal: {e}\r\n")
                self._chan.exit(1)
            except Exception:
                pass

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
                gw_log.error("Gateway terminal write error: %s", e)

    def eof_received(self):
        if self._session_type == "exec" and not self._exec_completed:
            return True
        if self._session_type == "shell":
            return True
        return False

    def connection_lost(self, exc):
        if self._session_type == "exec" and not self._exec_completed:
            return
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if exc:
            gw_log.error("Gateway connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.create_task(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.create_task(self._term.stop())
            self._term = None
        if self._session_type == "shell" and self._started_at:
            asyncio.create_task(
                _close_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip,
                    self._started_at,
                    terminal_type=self._terminal_type,
                    terminal_rows=self._terminal_rows,
                    terminal_cols=self._terminal_cols,
                )
            )
            gw_log.info(
                "Gateway session ended user=%s agent=%s duration=%ds",
                self._user.username, self._agent.agent_id,
                int((djangotime.now() - self._started_at).total_seconds()),
            )
