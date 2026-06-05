import asyncio
import logging
import os
import sys
import uuid
from hashlib import sha256
import base64

import asyncssh
import msgpack
import nats
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone as djangotime

from logs.models import AuditLog
from tacticalrmm.constants import AuditActionType
from tacticalrmm.helpers import setup_nats_options

logger = logging.getLogger("trmm")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.DEBUG)
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_sh)
    logger.setLevel(logging.DEBUG)


def _fingerprint(key_bytes: bytes) -> str:
    digest = sha256(key_bytes).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


@sync_to_async
def _lookup_key(fp: str):
    from accounts.models import SSHPublicKey
    try:
        return SSHPublicKey.objects.select_related("user").get(fingerprint=fp)
    except SSHPublicKey.DoesNotExist:
        return None


@sync_to_async
def _resolve_and_check(user, agent_id: str):
    from agents.models import Agent
    if user.is_superuser:
        try:
            return Agent.objects.get(agent_id=agent_id)
        except Agent.DoesNotExist:
            return None
    role = user.get_and_set_role_cache()
    if role and getattr(role, "is_superuser", False):
        try:
            return Agent.objects.get(agent_id=agent_id)
        except Agent.DoesNotExist:
            return None
    if not role:
        return None
    if not getattr(role, "can_use_terminal", False):
        return None

    try:
        agent = Agent.objects.defer("wmi_detail", "services").select_related(
            "site__client"
        ).get(agent_id=agent_id)
    except Agent.DoesNotExist:
        return None

    can_view_clients = role.can_view_clients.all() if role else None
    can_view_sites = role.can_view_sites.all() if role else None

    if not can_view_clients and not can_view_sites:
        return agent
    if can_view_clients and agent.client in can_view_clients:
        return agent
    if can_view_sites and agent.site in can_view_sites:
        return agent
    return None


@sync_to_async
def _record_session_and_audit(user, agent, session_id, remote_ip):
    from accounts.models import SSHSession
    now = djangotime.now()
    SSHSession.objects.create(
        user=user,
        agent=agent,
        session_id=session_id,
        remote_ip=remote_ip,
        started_at=now,
        client_version="",
    )
    AuditLog.audit_ssh_session_start(
        username=user.username,
        agent=agent,
        session_id=session_id,
        remote_ip=remote_ip,
    )


@sync_to_async
def _close_session_and_audit(user, agent, session_id, remote_ip, started_at):
    from accounts.models import SSHSession
    now = djangotime.now()
    duration = int((now - started_at).total_seconds())
    SSHSession.objects.filter(session_id=session_id).update(closed_at=now)
    AuditLog.audit_ssh_session_end(
        username=user.username,
        agent=agent,
        session_id=session_id,
        remote_ip=remote_ip,
        started_at=str(started_at),
        closed_at=str(now),
        duration=duration,
    )


class NATSTerminal:
    def __init__(self, agent, session_id, shell):
        self.agent = agent
        self.session_id = session_id
        self.shell = shell
        self.nc = None
        self.sub = None
        self._lock = asyncio.Lock()

    async def start(self, output_cb):
        sys.stderr.write(f"DEBUG: NATSTerminal.start connecting to NATS for {self.agent.agent_id}\n")
        sys.stderr.flush()
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)
        sys.stderr.write(f"DEBUG: NATSTerminal.start NATS connected\n")
        sys.stderr.flush()
        subj_out = f"{self.agent.agent_id}.terminal.{self.session_id}"
        sys.stderr.write(f"DEBUG: NATSTerminal.start subscribing to {subj_out}\n")
        sys.stderr.flush()

        async def handler(msg):
            sys.stderr.write(f"DEBUG: NATSTerminal handler received msg, data={msg.data[:100] if len(msg.data) > 100 else msg.data}\n")
            sys.stderr.flush()
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
                    asyncio.ensure_future(self.stop())
            elif isinstance(obj, (bytes, bytearray)):
                await output_cb(obj.decode("utf-8", errors="replace"))
            elif isinstance(obj, str):
                await output_cb(obj)

        self.sub = await self.nc.subscribe(subj_out, cb=handler)
        sys.stderr.write(f"DEBUG: NATSTerminal.start subscribed, publishing terminal_start\n")
        sys.stderr.flush()
        await self._pub({"func": "terminal_start", "payload": {"session_id": self.session_id, "shell": self.shell}})
        sys.stderr.write(f"DEBUG: NATSTerminal.start published terminal_start, returning\n")
        sys.stderr.flush()

    async def _pub(self, p):
        async with self._lock:
            await self.nc.publish(self.agent.agent_id, msgpack.dumps(p))

    async def write(self, data):
        sys.stderr.write(f"DEBUG: NATSTerminal.write len={len(data)}\n")
        sys.stderr.flush()
        await self._pub({"func": "terminal_input", "payload": {"session_id": self.session_id, "data": data}})

    async def resize(self, rows, cols):
        await self._pub({"func": "terminal_resize", "payload": {"session_id": self.session_id, "rows": str(rows), "cols": str(cols)}})

    async def stop(self):
        try:
            await self._pub({"func": "terminal_kill", "payload": {"session_id": self.session_id}})
        except Exception:
            pass
        if self.sub:
            try:
                await self.sub.unsubscribe()
            except Exception:
                pass
            self.sub = None
        if self.nc and not self.nc.is_closed:
            try:
                await self.nc.close()
            except Exception:
                pass
            self.nc = None


class SSHSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, agent, session_id, remote_ip):
        super().__init__()
        self._user = user
        self._agent = agent
        self._session_id = session_id
        self._remote_ip = remote_ip
        self._term = None
        self._chan = None
        self._started_at = None

    def connection_made(self, chan):
        self._chan = chan
        try:
            peer_name = chan.get_extra_info("peername", ("", ""))
            self._remote_ip = peer_name[0] if peer_name else self._remote_ip
            self._started_at = djangotime.now()
            shell = self._agent.effective_default_shell
            self._term = NATSTerminal(self._agent, self._session_id, shell)
            asyncio.ensure_future(self._start()).add_done_callback(self._on_start_done)
            asyncio.ensure_future(
                _record_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip
                )
            )
        except Exception as e:
            logger.error("SSH connection_made failed: %s", e, exc_info=True)
            raise

    def _on_start_done(self, fut):
        exc = fut.exception()
        if exc:
            sys.stderr.write(f"DEBUG: _start failed: {exc}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            logger.error("SSHSessionHandler._start failed: %s", exc, exc_info=exc)
        else:
            sys.stderr.write(f"DEBUG: _start completed successfully\n")
            sys.stderr.flush()

    async def _start(self):
        sys.stderr.write(f"DEBUG: _start running for {self._session_id}\n")
        sys.stderr.flush()
        async def output_cb(data, done=False, exit_code=None):
            sys.stderr.write(f"DEBUG: output_cb called, done={done}, data_type={type(data).__name__}, data={repr(data[:50]) if data else None}\n")
            sys.stderr.flush()
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                if self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                    sys.stderr.write(f"DEBUG: output_cb wrote {len(data)} chars\n")
                    sys.stderr.flush()
                else:
                    sys.stderr.write(f"DEBUG: output_cb skipped (chan={self._chan}, is_closing={self._chan.is_closing() if self._chan else 'N/A'})\n")
                    sys.stderr.flush()
                if done:
                    sys.stderr.write(f"DEBUG: output_cb done, calling chan.exit({exit_code or 0})\n")
                    sys.stderr.flush()
                    self._chan.exit(exit_code or 0)
            except Exception as e:
                sys.stderr.write(f"DEBUG: output_cb exception: {e}\n")
                import traceback
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

        sys.stderr.write(f"DEBUG: _start calling term.start for {self._session_id}\n")
        sys.stderr.flush()
        await self._term.start(output_cb)
        sys.stderr.write(f"DEBUG: _start term.start returned (this is normal - NATSTerminal.start is async but only publishes)\n")
        sys.stderr.flush()

    def shell_requested(self):
        sys.stderr.write(f"DEBUG: shell_requested called, returning True\n")
        sys.stderr.flush()
        return True

    def pty_requested(self, term_type, term_size, term_modes):
        sys.stderr.write(f"DEBUG: pty_requested term_type={term_type}\n")
        sys.stderr.flush()
        return True

    def terminal_modes(self):
        sys.stderr.write(f"DEBUG: terminal_modes called\n")
        sys.stderr.flush()
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

    def session_started(self):
        sys.stderr.write(f"DEBUG: session_started called\n")
        sys.stderr.flush()

    def exec_requested(self, command):
        sys.stderr.write(f"DEBUG: exec_requested command={command}\n")
        sys.stderr.flush()
        return True

    def data_received(self, data, datatype):
        sys.stderr.write(f"DEBUG: data_received len={len(data)} data={repr(data[:50])}\n")
        sys.stderr.flush()
        if self._term:
            asyncio.ensure_future(self._term.write(data))

    def connection_lost(self, exc):
        sys.stderr.write(f"DEBUG: connection_lost exc={exc}\n")
        sys.stderr.flush()
        if self._term:
            asyncio.ensure_future(self._term.stop())
        if exc:
            logger.error("SSH connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.ensure_future(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.ensure_future(self._term.stop())
        if self._started_at:
            asyncio.ensure_future(
                _close_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip, self._started_at
                )
            )


class SSHAgentServer(asyncssh.SSHServer):
    def __init__(self):
        self._auth_user = None
        self._auth_agent = None
        self._session_id = uuid.uuid4().hex
        self._conn = None

    def connection_made(self, conn):
        self._conn = conn

    async def begin_auth(self, username):
        sys.stderr.write(f"DEBUG: begin_auth username={username}\n")
        sys.stderr.flush()
        self._auth_user = None
        self._auth_agent = None
        self._session_id = uuid.uuid4().hex
        return True

    def public_key_auth_supported(self):
        return True

    def password_auth_supported(self):
        return False

    def kbdint_auth_supported(self):
        return False

    async def validate_public_key(self, username, key):
        try:
            sys.stderr.write(f"DEBUG: validate_public_key username={username}\n")
            sys.stderr.flush()
            if hasattr(key, 'public_data'):
                raw = key.public_data
            else:
                raw = key.get_public_key_bytes()
            fp = _fingerprint(raw)
            sys.stderr.write(f"DEBUG: fingerprint={fp}\n")
            sys.stderr.flush()

            ssh_key = await _lookup_key(fp)
            if ssh_key is None:
                sys.stderr.write(f"DEBUG: key not found for fingerprint {fp}\n")
                sys.stderr.flush()
                logger.warning("SSH: unknown key %s", fp)
                return False

            user = ssh_key.user
            sys.stderr.write(f"DEBUG: user={user.username}\n")
            sys.stderr.flush()
            if not user.is_active or user.block_dashboard_login:
                sys.stderr.write(f"DEBUG: user inactive or block_dashboard_login\n")
                sys.stderr.flush()
                logger.warning("SSH: inactive user %s", user.username)
                return False

            agent = await _resolve_and_check(user, username)
            if agent is None:
                sys.stderr.write(f"DEBUG: agent not found for user={user.username} username={username}\n")
                sys.stderr.flush()
                logger.warning("SSH: denied user=%s agent=%s", user.username, username)
                return False

            self._auth_user = user
            self._auth_agent = agent
            sys.stderr.write(f"DEBUG: auth success user={user.username} agent={agent.agent_id}\n")
            sys.stderr.flush()
            return True
        except Exception as e:
            sys.stderr.write(f"DEBUG: validate_public_key exception: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            logger.error("SSH: validate_public_key error: %s", e, exc_info=True)
            return False

    def session_requested(self):
        sys.stderr.write(f"DEBUG: session_requested called, _auth_user={self._auth_user}, _auth_agent={self._auth_agent}\n")
        sys.stderr.flush()
        try:
            if not self._auth_user or not self._auth_agent:
                sys.stderr.write(f"DEBUG: session_requested returning None (no auth)\n")
                sys.stderr.flush()
                return None
            sys.stderr.write(f"DEBUG: session_requested creating handler for {self._auth_user.username}\n")
            sys.stderr.flush()
            handler = SSHSessionHandler(
                self._auth_user, self._auth_agent, self._session_id, ""
            )
            sys.stderr.write(f"DEBUG: session_requested returning handler (no custom channel)\n")
            sys.stderr.flush()
            return handler
        except Exception as e:
            sys.stderr.write(f"DEBUG: session_requested exception: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            logger.error("SSH: session_requested error: %s", e, exc_info=True)
            return None


async def start_ssh_server(host="0.0.0.0", port=2222):
    host_key_path = getattr(settings, "SSH_HOST_KEY", "/etc/trmm/ssh_host_key")

    if not os.path.exists(host_key_path):
        logger.warning("SSH host key not found at %s, generating...", host_key_path)
        os.makedirs(os.path.dirname(host_key_path), exist_ok=True)
        key = asyncssh.generate_private_key("ssh-rsa")
        key.write_private_key(host_key_path)

    server_host_keys = [host_key_path]

    server = await asyncssh.create_server(
        SSHAgentServer,
        host,
        port,
        server_host_keys=server_host_keys,
        public_key_auth=True,
        password_auth=False,
        kbdint_auth=False,
        kex_algs=["mlkem768x25519-sha256", "curve25519-sha256"],
        line_editor=False,
    )
    logger.info("SSH gateway listening on %s:%s", host, port)
    return server
