import asyncio

import msgpack
import nats
from django.utils import timezone as djangotime

from .audit import (
    _audit_terminal_command,
    _close_session_and_audit,
    _record_session_and_audit,
)
from .constants import _strip_ansi, get_local_ips, build_welcome_message
from .logger import gw_log
from tacticalrmm.helpers import setup_nats_options


class TerminalProxy:
    def __init__(self, agent, session_id, shell):
        self.agent = agent
        self.session_id = session_id
        self.shell = shell
        self.nc = None
        self.sub = None
        self._lock = asyncio.Lock()

    async def start(self, output_cb):
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)
        subj_out = f"{self.agent.agent_id}.terminal.{self.session_id}"

        async def handler(msg):
            try:
                obj = msgpack.loads(msg.data)
            except Exception:
                obj = msg.data
            if isinstance(obj, dict):
                out = obj.get("output", b"")
                done = obj.get("done", False)
                ec = obj.get("exit_code")
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                await output_cb(out, done=done, exit_code=ec)
                if done:
                    asyncio.create_task(self.stop())
            elif isinstance(obj, (bytes, bytearray)):
                await output_cb(obj.decode("utf-8", errors="replace"))
            elif isinstance(obj, str):
                await output_cb(obj)

        self.sub = await self.nc.subscribe(subj_out, cb=handler)
        await self._pub({"func": "terminal_start", "payload": {"session_id": self.session_id, "shell": self.shell}})

    async def _pub(self, p):
        async with self._lock:
            await self.nc.publish(self.agent.agent_id, msgpack.dumps(p))

    async def write(self, data):
        await self._pub({"func": "terminal_input", "payload": {"session_id": self.session_id, "data": data}})

    async def resize(self, rows, cols):
        await self._pub({"func": "terminal_resize", "payload": {"session_id": self.session_id, "rows": str(rows), "cols": str(cols)}})

    async def stop(self):
        try:
            await self._pub({"func": "terminal_kill", "payload": {"session_id": self.session_id}})
        except Exception as e:
            gw_log.debug("TerminalProxy stop: failed to send kill: %s", e)
        if self.sub:
            try:
                await self.sub.unsubscribe()
            except Exception as e:
                gw_log.debug("TerminalProxy stop: failed to unsubscribe: %s", e)
            self.sub = None
        if self.nc and not self.nc.is_closed:
            try:
                await self.nc.close()
            except Exception as e:
                gw_log.debug("TerminalProxy stop: failed to close NATS connection: %s", e)
            self.nc = None


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
        gw_log.error("Gateway terminal welcome write failed: %s", e)

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
            gw_log.error("Gateway terminal output_cb error: %s", e)

    try:
        await term.start(output_cb)
    except Exception as e:
        gw_log.error("Gateway terminal start failed: %s", e, exc_info=True)
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
