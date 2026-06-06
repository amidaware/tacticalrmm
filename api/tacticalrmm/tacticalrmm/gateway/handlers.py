import asyncio
import logging

import asyncssh
from django.utils import timezone as djangotime

from .audit import _close_session_and_audit, _record_session_and_audit
from .exec import CmdProxy
from .terminal import TerminalProxy

logger = logging.getLogger("trmm")


class DirectSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, agent, session_id, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint=""):
        super().__init__()
        self._user = user
        self._agent = agent
        self._session_id = session_id
        self._remote_ip = remote_ip
        self._client_version = client_version
        self._ssh_key_name = ssh_key_name
        self._ssh_key_type = ssh_key_type
        self._ssh_key_fingerprint = ssh_key_fingerprint
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
        self._session_type = "exec"
        self._exec_cmd = command
        asyncio.create_task(self._start_exec())
        return True

    async def _start_exec(self):
        async def output_cb(data, done=False, exit_code=None):
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                if self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                if done:
                    self._exec_completed = True
                    asyncio.create_task(_close_session_and_audit(
                        self._user, self._agent, self._session_id, self._remote_ip,
                        self._started_at,
                    ))
                    if self._chan and not self._chan.is_closing():
                        await self._chan.exit(exit_code or 0)
            except Exception:
                logger.error("Gateway exec output_cb error", exc_info=True)

        try:
            self._exec = CmdProxy(self._agent, self._session_id, self._exec_cmd)
            await self._exec.start(output_cb)
        except Exception as e:
            logger.error("Gateway exec start failed: %s", e, exc_info=True)
            try:
                await self._chan.write(f"\r\nFailed to execute command: {e}\r\n")
                await self._chan.exit(1)
            except Exception:
                pass

    def shell_requested(self):
        self._session_type = "shell"
        shell = self._agent.effective_default_shell
        self._term = TerminalProxy(self._agent, self._session_id, shell)
        role_name = "None"
        if self._user.role:
            role_name = self._user.role.name
        self._chan.write(
            f"\r\n\x1b[32mWelcome, \x1b[1m{self._user.username}\x1b[0m\x1b[32m [Role: {role_name}]\x1b[0m\r\n\r\n"
        )
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
                if self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                if done:
                    asyncio.create_task(_close_session_and_audit(
                        self._user, self._agent, self._session_id, self._remote_ip,
                        self._started_at,
                        terminal_type=self._terminal_type,
                        terminal_rows=self._terminal_rows,
                        terminal_cols=self._terminal_cols,
                    ))
                    await self._chan.exit(exit_code or 0)
            except Exception:
                logger.error("Gateway terminal output_cb error", exc_info=True)

        try:
            await self._term.start(output_cb)
        except Exception as e:
            logger.error("Gateway terminal start failed: %s", e, exc_info=True)
            await self._chan.write(f"\r\nFailed to start terminal: {e}\r\n")
            self._chan.exit(1)

    def pty_requested(self, term_type, term_size, term_modes):
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
            asyncio.create_task(self._term.write(data))

    def eof_received(self):
        if self._session_type == "exec" and not self._exec_completed:
            return False
        return True

    def connection_lost(self, exc):
        if self._session_type == "exec" and not self._exec_completed:
            return
        if self._term:
            asyncio.create_task(self._term.stop())
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
