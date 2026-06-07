import asyncio

import asyncssh
from django.utils import timezone as djangotime

from .audit import (
    _audit_exec_command,
    _close_session_and_audit,
)
from .constants import ANSI_ESCAPE
from .exec import CmdProxy
from .logger import gw_log


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


async def run_exec(user, agent, session_id, command, output_cb):
    exec_proxy = CmdProxy(agent, session_id, command)
    await exec_proxy.start(output_cb)


async def run_terminal(term, output_cb):
    await term.start(output_cb)


class ExecSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, agent, session_id, command, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint=""):
        super().__init__()
        self._user = user
        self._agent = agent
        self._session_id = session_id
        self._command = command
        self._remote_ip = remote_ip
        self._client_version = client_version
        self._ssh_key_name = ssh_key_name
        self._ssh_key_type = ssh_key_type
        self._ssh_key_fingerprint = ssh_key_fingerprint
        self._chan = None
        self._started_at = None
        self._completed = False

    def connection_made(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
            gw_log.info(
                "Gateway exec session user=%s agent=%s remote_ip=%s cmd=%s",
                self._user.username, self._agent.agent_id, self._remote_ip, self._command,
            )
        except Exception as e:
            gw_log.error("Gateway exec connection_made failed: %s", e, exc_info=True)
            raise
        asyncio.create_task(self._start_exec())

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
                    self._completed = True
                    asyncio.create_task(_audit_exec_command(
                        self._user, self._agent, self._command, exit_code,
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
            await run_exec(self._user, self._agent, self._session_id, self._command, output_cb)
        except Exception as e:
            gw_log.error("Gateway exec start failed: %s", e, exc_info=True)
            try:
                self._chan.write(f"\r\nFailed to execute command: {e}\r\n")
                self._chan.exit(1)
            except Exception:
                pass

    def eof_received(self):
        if not self._completed:
            return True
        return False

    def connection_lost(self, exc):
        if not self._completed:
            return
        if exc:
            gw_log.error("Gateway exec connection lost: %s", exc)

    def closed(self):
        if self._started_at:
            asyncio.create_task(
                _close_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip,
                    self._started_at,
                )
            )