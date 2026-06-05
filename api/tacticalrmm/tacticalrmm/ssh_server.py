import asyncio
import logging
import os
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
                    asyncio.ensure_future(self.stop())
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
            logger.error("SSHSessionHandler._start failed: %s", exc, exc_info=exc)

    async def _start(self):
        async def output_cb(data, done=False, exit_code=None):
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                if self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                if done:
                    self._chan.exit(exit_code or 0)
            except Exception:
                logger.error("SSH output_cb error", exc_info=True)

        await self._term.start(output_cb)

    def shell_requested(self):
        return True

    def pty_requested(self, term_type, term_size, term_modes):
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


    def exec_requested(self, command):
        return True

    def data_received(self, data, datatype):
        if self._term:
            asyncio.ensure_future(self._term.write(data))

    def connection_lost(self, exc):
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
            if hasattr(key, 'public_data'):
                raw = key.public_data
            else:
                raw = key.get_public_key_bytes()
            fp = _fingerprint(raw)

            ssh_key = await _lookup_key(fp)
            if ssh_key is None:
                logger.warning("SSH: unknown key %s", fp)
                return False

            user = ssh_key.user
            if not user.is_active or user.block_dashboard_login:
                logger.warning("SSH: inactive user %s", user.username)
                return False

            agent = await _resolve_and_check(user, username)
            if agent is None:
                logger.warning("SSH: denied user=%s agent=%s", user.username, username)
                return False

            self._auth_user = user
            self._auth_agent = agent
            return True
        except Exception as e:
            logger.error("SSH: validate_public_key error: %s", e, exc_info=True)
            return False

    def session_requested(self):
        try:
            if not self._auth_user or not self._auth_agent:
                return None
            handler = SSHSessionHandler(
                self._auth_user, self._auth_agent, self._session_id, ""
            )
            return handler
        except Exception as e:
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
        login_timeout=30,
        keepalive_interval=30,
        keepalive_count_max=3,
    )
    logger.info("SSH gateway listening on %s:%s", host, port)
    return server
