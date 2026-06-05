import asyncio
import collections
import logging
import os
import time
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

_active_connections = 0


def get_active_connections() -> int:
    return _active_connections


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
def _record_session_and_audit(
    user, agent, session_id, remote_ip, client_version="",
    ssh_key_name="", ssh_key_type="", ssh_key_fingerprint="",
):
    from accounts.models import SSHSession
    now = djangotime.now()
    SSHSession.objects.create(
        user=user,
        agent=agent,
        session_id=session_id,
        remote_ip=remote_ip,
        started_at=now,
        client_version=client_version,
    )
    AuditLog.audit_ssh_session_start(
        username=user.username,
        agent=agent,
        session_id=session_id,
        remote_ip=remote_ip,
        client_version=client_version,
        ssh_key_name=ssh_key_name,
        ssh_key_type=ssh_key_type,
        ssh_key_fingerprint=ssh_key_fingerprint,
    )


@sync_to_async
def _close_session_and_audit(
    user, agent, session_id, remote_ip, started_at,
    terminal_type="", terminal_rows=0, terminal_cols=0,
):
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
        terminal_type=terminal_type,
        terminal_rows=terminal_rows,
        terminal_cols=terminal_cols,
    )


@sync_to_async
def _audit_session_failed(
    username, agent_id, remote_ip, reason,
    ssh_key_name="", ssh_key_type="", ssh_key_fingerprint="",
):
    AuditLog.audit_ssh_session_failed(
        username=username,
        agent_id=agent_id,
        remote_ip=remote_ip,
        reason=reason,
        ssh_key_name=ssh_key_name,
        ssh_key_type=ssh_key_type,
        ssh_key_fingerprint=ssh_key_fingerprint,
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
            shell = self._agent.effective_default_shell
            self._term = NATSTerminal(self._agent, self._session_id, shell)
            asyncio.ensure_future(self._start()).add_done_callback(self._on_start_done)
            asyncio.ensure_future(
                _record_session_and_audit(
                    self._user, self._agent, self._session_id, self._remote_ip,
                    client_version=self._client_version,
                    ssh_key_name=self._ssh_key_name,
                    ssh_key_type=self._ssh_key_type,
                    ssh_key_fingerprint=self._ssh_key_fingerprint,
                )
            )
            logger.info(
                "SSH session started user=%s agent=%s remote_ip=%s client=%s",
                self._user.username, self._agent.agent_id, self._remote_ip, self._client_version,
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
                    self._user, self._agent, self._session_id, self._remote_ip,
                    self._started_at,
                    terminal_type=self._terminal_type,
                    terminal_rows=self._terminal_rows,
                    terminal_cols=self._terminal_cols,
                )
            )
            logger.info(
                "SSH session ended user=%s agent=%s duration=%ds",
                self._user.username, self._agent.agent_id,
                int((djangotime.now() - self._started_at).total_seconds()),
            )


@sync_to_async
def _get_menu_agents(user):
    from agents.models import Agent
    agents = Agent.objects.select_related("site__client").only(
        "agent_id", "hostname", "public_ip", "last_seen",
        "offline_time", "overdue_time",
        "site__name", "site__client__name",
    )

    if user.is_superuser:
        filtered = list(agents)
    else:
        role = user.get_and_set_role_cache()
        if not (role and getattr(role, "can_use_terminal", False)):
            return []
        can_view_clients = list(role.can_view_clients.all()) if role.can_view_clients.exists() else None
        can_view_sites = list(role.can_view_sites.all()) if role.can_view_sites.exists() else None
        filtered = []
        for a in agents:
            if can_view_clients and a.client not in can_view_clients:
                continue
            if can_view_sites and a.site not in can_view_sites:
                continue
            filtered.append(a)

    tree = {}
    for a in filtered:
        client_name = a.site.client.name
        site_name = a.site.name
        tree.setdefault(client_name, {}).setdefault(site_name, []).append(
            (a.agent_id, a.hostname, a.public_ip or "", a.status)
        )
    return tree


class MenuSessionHandler(asyncssh.SSHServerSession):
    def __init__(self, user, session_id, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint=""):
        super().__init__()
        self._user = user
        self._session_id = session_id
        self._remote_ip = remote_ip
        self._client_version = client_version
        self._ssh_key_name = ssh_key_name
        self._ssh_key_type = ssh_key_type
        self._ssh_key_fingerprint = ssh_key_fingerprint
        self._chan = None
        self._term = None
        self._started_at = None
        self._selected_agent = None
        self._tree = []
        self._buf = ""
        self._state = "client"  # client / site / agent / terminal
        self._menu_client = ""
        self._menu_site = ""
        self._agent_id = ""

    def connection_made(self, chan):
        self._chan = chan
        self._started_at = djangotime.now()
        asyncio.ensure_future(self._enter_menu())

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
        return False

    def data_received(self, data, datatype):
        if self._state == "terminal":
            if self._term:
                asyncio.ensure_future(self._term.write(data))
            return
        self._buf += data.decode("utf-8", errors="replace")
        if "\n" in self._buf:
            line = self._buf.strip()
            self._buf = ""
            asyncio.ensure_future(self._handle_input(line))

    def connection_lost(self, exc):
        if self._term:
            asyncio.ensure_future(self._term.stop())
        if exc:
            logger.error("SSH menu connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.ensure_future(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.ensure_future(self._term.stop())
        if self._started_at and self._selected_agent:
            asyncio.ensure_future(
                _close_session_and_audit(
                    self._user, self._selected_agent, self._session_id,
                    self._remote_ip, self._started_at,
                )
            )

    async def _write(self, text=""):
        if self._chan and not self._chan.is_closing():
            self._chan.write(text)

    async def _enter_menu(self):
        self._tree = await _get_menu_agents(self._user)
        if not self._tree:
            await self._write(
                "\r\nNo agents available. You don't have permission "
                "to access any agents, or no agents exist.\r\n"
            )
            self._chan.exit(1)
            return
        logger.info(
            "SSH menu session started user=%s remote_ip=%s",
            self._user.username, self._remote_ip,
        )
        await self._show_clients()

    async def _show_clients(self):
        self._state = "client"
        clients = sorted(self._tree.keys())
        banner = (
            "\x1b[2m"
            "                     AAAAAAAAA  AAAAAAAAA                             \r\n"
            "                     AAAAAAAAAAAAA  AAAAAAAAAAAAA                     \r\n"
            "                  AAAAAAAAAAAAAAAA  AAAAAAAAAAAAAAAA                   \r\n"
            "                AAAAAAAAAA                  AAAAAAAAAA                 \r\n"
            "              AAAAAAAAA                        AAAAAAAAA               \r\n"
            "            AAAAAAAA                              AAAAAAAA             \r\n"
            "           AAAAAAA                                  AAAAAAA            \r\n"
            "         AAAAAAAA                                    AAAAAAA           \r\n"
            "        AAAAAAA                                        AAAAAAA         \r\n"
            "       AAAAAAA      AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA      AAAAAA         \r\n"
            "       AAAAAA       AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA       AAAAAA        \r\n"
            "      AAAAAAA       AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA       AAAAAAA       \r\n"
            "      AAAAAA        AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA        AAAAAA       \r\n"
            "     AAAAAAA                  AAAAAAAAA                   AAAAAA       \r\n"
            "     AAAAAAA                   AAAAAAAA                    AAAAAA      \r\n"
            "     AAAAAA                     AAAAAA                     AAAAAA      \r\n"
            "     AAAAAA                    AAAAAAAA                    AAAAAA      \r\n"
            "     AAAAAAA             AAA   AAAAAAAA   AAA             AAAAAA       \r\n"
            "      AAAAAA            AAAAA  AAAAAAAA  AAAAA            AAAAAA       \r\n"
            "      AAAAAA          AAAAAAA  AAAAAAAA  AAAAAAA          AAAAAA       \r\n"
            "       AAAAAA         AAAAAAA  AAAAAAAA  AAAAAAA         AAAAAA        \r\n"
            "       AAAAAAA        AAAAAAA  AAAAAAAA  AAAAAAA        AAAAAAA        \r\n"
            "        AAAAAAA       AAAAAAA  AAAAAAAA  AAAAAAA       AAAAAAA         \r\n"
            "         AAAAAAA      AAAAAAA  AAAAAAAA  AAAAAAA      AAAAAAA          \r\n"
            "          AAAAAAAA    AAAAAAA  AAAAAAAA  AAAAAAA    AAAAAAAA           \r\n"
            "            AAAAAAAA  AAAAAAA  AAAAAAAA  AAAAAAA  AAAAAAAA             \r\n"
            "             AAAAAAAAAAAAAAAA  AAAAAAAA  AAAAAAAAAAAAAAAA              \r\n"
            "               AAAAAAAAAAAAAA  AAAAAAAA  AAAAAAAAAAAAAA                \r\n"
            "                  AAAAAAAAAAA  AAAAAAAA  AAAAAAAAAAA                   \r\n"
            "                    AAAAAAAAA  AAAAAAAA  AAAAAAAAA                     \r\n"
            "                       AAAAAA  AAAAAAAA  AAAAA                        \r\n"
            "\x1b[0m"
        )
        lines = [
            "",
            banner,
            "\x1b[1mTactical RMM SSH Gateway\x1b[0m",
            "\x1b[2mSelect a client to browse its agents\x1b[0m",
            "",
        ]
        for i, name in enumerate(clients, 1):
            total = sum(len(agents) for agents in self._tree[name].values())
            lines.append(f"  {i:>2}. {name}  ({total} agent{'s' if total != 1 else ''})")
        lines += [
            "",
            "  \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _show_sites(self):
        self._state = "site"
        sites = sorted(self._tree[self._menu_client].keys())
        lines = [
            f"\r\n\x1b[1mClient: {self._menu_client}\x1b[0m",
            "\x1b[2mSelect a site\x1b[0m",
            "",
        ]
        for i, name in enumerate(sites, 1):
            count = len(self._tree[self._menu_client][name])
            lines.append(f"  {i:>2}. {name}  ({count} agent{'s' if count != 1 else ''})")
        lines += [
            "",
            "  \x1b[2m b. Back to clients\x1b[0m",
            "  \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _show_agents(self):
        self._state = "agent"
        agents = self._tree[self._menu_client][self._menu_site]
        lines = [
            f"\r\n\x1b[1m{self._menu_client} \x1b[2m>\x1b[0m {self._menu_site}\x1b[0m",
            "\x1b[2mSelect an agent\x1b[0m",
            "",
        ]
        for i, (aid, hostname, ip, status) in enumerate(agents, 1):
            status_color = "\x1b[32m" if status == "online" else "\x1b[31m"
            ip_str = f" ({ip})" if ip else ""
            lines.append(
                f"  {i:>2}. {hostname}{ip_str}"
                f"  {status_color}{status}\x1b[0m"
            )
        lines += [
            "",
            "  \x1b[2m b. Back to sites\x1b[0m",
            "  \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _handle_input(self, line):
        line = line.strip().lower()
        if line in ("q", "quit", "exit"):
            await self._write("\r\nGoodbye.\r\n")
            self._chan.exit(0)
            return

        if self._state == "client":
            if line == "b":
                return
            clients = sorted(self._tree.keys())
            try:
                idx = int(line) - 1
                if 0 <= idx < len(clients):
                    self._menu_client = clients[idx]
                    await self._show_sites()
                else:
                    await self._write("\r\nInvalid choice. Try again: ")
            except ValueError:
                await self._write("\r\nEnter a number: ")

        elif self._state == "site":
            if line == "b":
                await self._show_clients()
                return
            sites = sorted(self._tree[self._menu_client].keys())
            try:
                idx = int(line) - 1
                if 0 <= idx < len(sites):
                    self._menu_site = sites[idx]
                    await self._show_agents()
                else:
                    await self._write("\r\nInvalid choice. Try again: ")
            except ValueError:
                await self._write("\r\nEnter a number: ")

        elif self._state == "agent":
            if line == "b":
                await self._show_sites()
                return
            agents = self._tree[self._menu_client][self._menu_site]
            try:
                idx = int(line) - 1
                if 0 <= idx < len(agents):
                    aid, hostname, ip, status = agents[idx]
                    if status != "online":
                        await self._write(
                            f"\r\n\x1b[31m{hostname} is {status}.\x1b[0m "
                            "Cannot connect.\r\n"
                        )
                        await self._show_agents()
                        return
                    await self._connect_to_agent(aid, hostname)
                else:
                    await self._write("\r\nInvalid choice. Try again: ")
            except ValueError:
                await self._write("\r\nEnter a number: ")

    async def _connect_to_agent(self, agent_id, hostname):
        from agents.models import Agent
        try:
            agent = await sync_to_async(
                lambda: Agent.objects.get(agent_id=agent_id)
            )()
        except Agent.DoesNotExist:
            await self._write(f"\r\nAgent {agent_id} not found.\r\n")
            return

        self._selected_agent = agent
        self._state = "terminal"
        shell = agent.effective_default_shell
        self._term = NATSTerminal(agent, self._session_id, shell)

        await self._write(
            f"\r\n\x1b[32mConnecting to {hostname} ({agent_id})...\x1b[0m\r\n\r\n"
        )

        asyncio.ensure_future(
            _record_session_and_audit(
                self._user, agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
        )
        logger.info(
            "SSH menu: user=%s connected to agent=%s hostname=%s",
            self._user.username, agent_id, hostname,
        )

        async def output_cb(data, done=False, exit_code=None):
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                if self._chan and not self._chan.is_closing():
                    self._chan.write(data)
                if done:
                    self._chan.exit(exit_code or 0)
            except Exception:
                logger.error("SSH menu output_cb error", exc_info=True)

        try:
            await self._term.start(output_cb)
        except Exception as e:
            logger.error("SSH menu: failed to start terminal: %s", e, exc_info=True)
            await self._write(f"\r\n\x1b[31mFailed to connect: {e}\x1b[0m\r\n")
            self._state = "agent"
            await self._show_agents()


class _RateLimiter:
    def __init__(self, max_attempts: int = 10, window: int = 60):
        self._max_attempts = max_attempts
        self._window = window
        self._attempts: dict[str, list[float]] = collections.defaultdict(list)

    def allow(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        attempts = self._attempts[ip]
        attempts[:] = [t for t in attempts if t > cutoff]
        if len(attempts) >= self._max_attempts:
            return False
        attempts.append(now)
        return True

    def reset(self, ip: str) -> None:
        self._attempts.pop(ip, None)


def _make_rate_limiter():
    return _RateLimiter(
        max_attempts=getattr(settings, "SSH_RATE_LIMIT_ATTEMPTS", 10),
        window=getattr(settings, "SSH_RATE_LIMIT_WINDOW", 60),
    )


_rate_limiter = _make_rate_limiter()


class SSHAgentServer(asyncssh.SSHServer):
    def __init__(self):
        self._auth_user = None
        self._auth_agent = None
        self._session_id = uuid.uuid4().hex
        self._conn = None
        self._remote_ip = ""
        self._client_version = ""
        self._ssh_key_name = ""
        self._ssh_key_type = ""
        self._ssh_key_fingerprint = ""
        self._is_menu = False

    def connection_made(self, conn):
        self._conn = conn
        try:
            peer = conn.get_extra_info("peername", ("", 0))
            self._remote_ip = peer[0] if peer else ""
            self._client_version = conn.get_extra_info("client_version", "")
            logger.info(
                "SSH connection from %s client=%s",
                self._remote_ip, self._client_version,
            )
        except Exception:
            self._remote_ip = ""
            self._client_version = ""
        global _active_connections
        _active_connections += 1

    def connection_lost(self, exc):
        global _active_connections
        _active_connections -= 1
        if exc:
            logger.error("SSH connection from %s lost: %s", self._remote_ip, exc)

    async def begin_auth(self, username):
        self._auth_user = None
        self._auth_agent = None
        self._is_menu = False
        self._session_id = uuid.uuid4().hex
        if self._remote_ip and not _rate_limiter.allow(self._remote_ip):
            logger.warning("SSH: rate limit exceeded for %s", self._remote_ip)
            return False
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
                logger.warning("SSH: unknown key %s from %s", fp, self._remote_ip)
                return False

            user = ssh_key.user
            if not user.is_active or user.block_dashboard_login:
                logger.warning(
                    "SSH: inactive user %s from %s", user.username, self._remote_ip
                )
                return False

            self._ssh_key_name = ssh_key.name
            self._ssh_key_type = ssh_key.key_type
            self._ssh_key_fingerprint = ssh_key.fingerprint

            if username.lower() == "menu":
                role = await sync_to_async(user.get_and_set_role_cache)()
                if not user.is_superuser and not (role and getattr(role, "can_use_terminal", False)):
                    logger.warning(
                        "SSH: menu denied for user=%s from %s",
                        user.username, self._remote_ip,
                    )
                    return False
                self._auth_user = user
                self._auth_agent = None
                self._is_menu = True
                logger.info(
                    "SSH: menu session user=%s key=%s from %s",
                    user.username, ssh_key.name, self._remote_ip,
                )
                return True

            agent = await _resolve_and_check(user, username)
            if agent is None:
                logger.warning(
                    "SSH: denied user=%s agent=%s from %s",
                    user.username, username, self._remote_ip,
                )
                asyncio.ensure_future(
                    _audit_session_failed(
                        username=user.username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason="access_denied_no_permission",
                        ssh_key_name=ssh_key.name,
                        ssh_key_type=ssh_key.key_type,
                        ssh_key_fingerprint=ssh_key.fingerprint,
                    )
                )
                return False

            if agent.status != "online":
                logger.warning(
                    "SSH: denied user=%s agent=%s from %s reason=agent_%s",
                    user.username, username, self._remote_ip, agent.status,
                )
                asyncio.ensure_future(
                    _audit_session_failed(
                        username=user.username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason=f"agent_{agent.status}",
                        ssh_key_name=ssh_key.name,
                        ssh_key_type=ssh_key.key_type,
                        ssh_key_fingerprint=ssh_key.fingerprint,
                    )
                )
                return False

            self._auth_user = user
            self._auth_agent = agent
            logger.info(
                "SSH: auth success user=%s agent=%s key=%s from %s",
                user.username, username, ssh_key.name, self._remote_ip,
            )
            return True
        except Exception as e:
            logger.error("SSH: validate_public_key error: %s", e, exc_info=True)
            return False

    def session_requested(self):
        try:
            if self._is_menu:
                if not self._auth_user:
                    return None
                return MenuSessionHandler(
                    self._auth_user, self._session_id, self._remote_ip,
                    client_version=self._client_version,
                    ssh_key_name=self._ssh_key_name,
                    ssh_key_type=self._ssh_key_type,
                    ssh_key_fingerprint=self._ssh_key_fingerprint,
                )
            if not self._auth_user or not self._auth_agent:
                return None
            handler = SSHSessionHandler(
                self._auth_user, self._auth_agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
            return handler
        except Exception as e:
            logger.error("SSH: session_requested error: %s", e, exc_info=True)
            return None
            handler = SSHSessionHandler(
                self._auth_user, self._auth_agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
            )
            return handler
        except Exception as e:
            logger.error("SSH: session_requested error: %s", e, exc_info=True)
            return None


async def start_ssh_server(host=None, port=None):
    if host is None:
        host = getattr(settings, "SSH_SERVER_HOST", "0.0.0.0")
    if port is None:
        port = getattr(settings, "SSH_SERVER_PORT", 2222)

    host_key_path = getattr(settings, "SSH_HOST_KEY", "/etc/trmm/ssh_host_key")

    if not os.path.exists(host_key_path):
        logger.warning("SSH host key not found at %s, generating...", host_key_path)
        os.makedirs(os.path.dirname(host_key_path), exist_ok=True)
        key = asyncssh.generate_private_key("ssh-rsa")
        key.write_private_key(host_key_path)

    server_host_keys = [host_key_path]

    login_timeout = getattr(settings, "SSH_LOGIN_TIMEOUT", 30)
    keepalive_interval = getattr(settings, "SSH_KEEPALIVE_INTERVAL", 30)
    keepalive_count_max = getattr(settings, "SSH_KEEPALIVE_COUNT_MAX", 3)

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
        login_timeout=login_timeout,
        keepalive_interval=keepalive_interval,
        keepalive_count_max=keepalive_count_max,
        tcp_keepalive=True,
    )
    logger.info(
        "SSH gateway listening on %s:%s (timeout=%d keepalive=%d/%d)",
        host, port, login_timeout, keepalive_interval, keepalive_count_max,
    )
    return server
