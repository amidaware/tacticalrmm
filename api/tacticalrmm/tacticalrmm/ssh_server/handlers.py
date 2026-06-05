import asyncio
import logging
import random

import asyncssh
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone as djangotime

from .audit import _close_session_and_audit, _record_session_and_audit
from .highscores import _add_highscore, _format_highscores
from .terminal import NATSTerminal
from .utils import _get_user_group, _resolve_and_check
from .egg import EggGame

logger = logging.getLogger("trmm")


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
            (a.agent_id, a.hostname, a.public_ip or "", a.status, a.version, a.last_seen)
        )
    return tree


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
            asyncio.create_task(self._start()).add_done_callback(self._on_start_done)
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
        role_name = "None"
        if self._user.role:
            role_name = self._user.role.name
        self._chan.write(
            f"\r\n\x1b[32mWelcome, \x1b[1m{self._user.username}\x1b[0m\x1b[32m [Role: {role_name}]\x1b[0m\r\n\r\n"
        )
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
            asyncio.create_task(self._term.write(data))

    def connection_lost(self, exc):
        if self._term:
            asyncio.create_task(self._term.stop())
        if exc:
            logger.error("SSH connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.create_task(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.create_task(self._term.stop())
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
                "SSH session ended user=%s agent=%s duration=%ds",
                self._user.username, self._agent.agent_id,
                int((djangotime.now() - self._started_at).total_seconds()),
            )


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
        self._state = "client"
        self._menu_client = ""
        self._menu_site = ""
        self._agent_id = ""
        self._buf = ""
        self._last_activity = djangotime.now()

    def connection_made(self, chan):
        self._chan = chan
        self._started_at = djangotime.now()
        asyncio.create_task(self._enter_menu())
        asyncio.create_task(self._idle_check())

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
            asyncssh.ECHO: 1,
            asyncssh.ECHOE: 1,
            asyncssh.ECHOK: 1,
            asyncssh.ECHOKE: 1,
            asyncssh.ISIG: 1,
            asyncssh.ICANON: 0,
            asyncssh.VTIME: 0,
            asyncssh.VMIN: 1,
        }

    def exec_requested(self, command):
        return False

    def data_received(self, data, datatype):
        try:
            if self._state == "terminal":
                # Check for return-to-menu key (Ctrl+^ = 0x1e)
                if isinstance(data, bytes):
                    if b'\x1e' in data:
                        asyncio.create_task(self._return_from_terminal())
                        return
                else:
                    if '\x1e' in data:
                        asyncio.create_task(self._return_from_terminal())
                        return
                if self._term:
                    asyncio.create_task(self._term.write(data))
                return
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="replace")
            else:
                text = data
            if self._state == "snake_gameover":
                self._state = "client"
                asyncio.create_task(self._show_clients())
                return
            if self._state == "snake":
                for ch in text:
                    self._egg.handle_input(ch)
                return
            for ch in text:
                asyncio.create_task(self._handle_char(ch))
        except Exception as e:
            logger.error("SSH menu data_received error: %s", e, exc_info=True)

    def connection_lost(self, exc):
        if self._term:
            asyncio.create_task(self._term.stop())
        if exc:
            logger.error("SSH menu connection lost: %s", exc)

    def terminal_size_changed(self, w, h, pw, ph):
        if self._term:
            asyncio.create_task(self._term.resize(h, w))

    def closed(self):
        if self._term:
            asyncio.create_task(self._term.stop())
        if self._started_at and self._selected_agent:
            asyncio.create_task(
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
        group = await _get_user_group(self._user) or "None"
        msg = f"\r\n\x1b[32mWelcome, \x1b[1m{self._user.username}\x1b[0m\x1b[32m [Role: {group}]\x1b[0m\r\n"
        await self._write(msg)
        logger.info(
            "SSH menu session started user=%s remote_ip=%s",
            self._user.username, self._remote_ip,
        )
        await self._show_clients()

    async def _show_clients(self):
        self._state = "client"
        clients = sorted(self._tree.keys())
        lines = [
            "",
            f"\x1b[1mTactical RMM SSH Gateway\x1b[0m \x1b[2mv{settings.TRMM_VERSION}\x1b[0m",
            "\x1b[2mSelect a client to browse its agents\x1b[0m",
            "",
        ]
        for i, name in enumerate(clients, 1):
            total = sum(len(agents) for agents in self._tree[name].values())
            lines.append(f"  {i:>2}. {name}  ({total} agent{'s' if total != 1 else ''})")
        lines += [
            "",
            "  \x1b[2m s. Search\x1b[0m   \x1b[2m r. Refresh\x1b[0m   \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _show_sites(self):
        self._state = "site"
        sites = sorted(self._tree[self._menu_client].keys())
        lines = [
            f"\r\n\x1b[1mClients \x1b[2m>\x1b[0m {self._menu_client}\x1b[0m",
            "\x1b[2mSelect a site\x1b[0m",
            "",
        ]
        for i, name in enumerate(sites, 1):
            count = len(self._tree[self._menu_client][name])
            lines.append(f"  {i:>2}. {name}  ({count} agent{'s' if count != 1 else ''})")
        lines += [
            "",
            "  \x1b[2m b. Back\x1b[0m   \x1b[2m r. Refresh\x1b[0m   \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _show_agents(self):
        self._state = "agent"
        agents = self._tree[self._menu_client][self._menu_site]
        lines = [
            f"\r\n\x1b[1mClients \x1b[2m>\x1b[0m {self._menu_client} \x1b[2m>\x1b[0m {self._menu_site}\x1b[0m",
            "\x1b[2mSelect an agent\x1b[0m",
            "",
        ]
        for i, (aid, hostname, ip, status, version, last_seen) in enumerate(agents, 1):
            status_color = "\x1b[32m" if status == "online" else "\x1b[31m"
            ip_str = f" ({ip})" if ip else ""
            version_str = f" v{version}" if version else ""
            last_seen_str = ""
            if last_seen:
                ago = djangotime.now() - last_seen
                minutes = int(ago.total_seconds() / 60)
                if minutes < 1:
                    last_seen_str = " (<1m ago)"
                elif minutes < 60:
                    last_seen_str = f" ({minutes}m ago)"
                else:
                    hours = minutes // 60
                    last_seen_str = f" ({hours}h ago)"
            lines.append(
                f"  {i:>2}. {hostname}{ip_str}{version_str}{last_seen_str}"
                f"  {status_color}{status}\x1b[0m"
            )
        lines += [
            "",
            "  \x1b[2m b. Back\x1b[0m   \x1b[2m r. Refresh\x1b[0m   \x1b[2m q. Quit\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _handle_char(self, ch):
        try:
            self._last_activity = djangotime.now()
            self._agent_page = 0
            self._agents_per_page = 10

            if ch in ("\r", "\n"):
                if self._buf.strip().isdigit():
                    num = int(self._buf.strip())
                    self._buf = ""
                    if self._state == "search_results":
                        await self._handle_search_result(num)
                    else:
                        await self._handle_number(num)
                    return
                if self._state == "search" and self._buf.strip():
                    query = self._buf.strip()
                    self._buf = ""
                    await self._search_agents(query)
                    return
                if self._buf:
                    cmd = self._buf.strip().lower()
                    self._buf = ""
                    if cmd == "egg":
                        self._egg = EggGame(self)
                        await self._egg.start()
                        return
                return

            if ch == "\x7f":
                if self._buf:
                    self._buf = self._buf[:-1]
                    self._chan.write("\x08 \x08")
                return

            if ch in ("q", "Q", "\x03"):
                self._buf = ""
                await self._write("\r\nGoodbye.\r\n")
                self._chan.exit(0)
                return

            if ch in ("b", "B"):
                self._buf = ""
                if self._state == "site":
                    await self._show_clients()
                elif self._state == "agent":
                    await self._show_sites()
                elif self._state == "search_results":
                    self._state = "client"
                    await self._show_clients()
                return

            if ch in ("s", "S"):
                if self._state == "client":
                    self._buf = ""
                    self._state = "search"
                    await self._write("\r\nSearch hostname: ")
                    return
                elif self._state == "search":
                    self._buf = ""
                    self._state = "client"
                    await self._show_clients()
                    return

            if ch in ("r", "R"):
                self._buf = ""
                await self._write("\r\nRefreshing...\r\n")
                self._tree = await _get_menu_agents(self._user)
                if not self._tree:
                    await self._write("\r\nNo agents available.\r\n")
                    self._chan.exit(1)
                    return
                if self._state in ("site", "agent") and self._menu_client not in self._tree:
                    self._state = "client"
                elif self._state == "agent" and self._menu_site not in self._tree.get(self._menu_client, {}):
                    self._state = "site"
                await self._show_current()
                return

            if ch in ("?", "h", "H"):
                await self._show_help()
                return

            if ch.isdigit():
                self._buf += ch
                self._chan.write(ch)
                return

            if ch.isprintable():
                self._buf += ch
                self._chan.write(ch)
                return
        except Exception as e:
            logger.error("SSH menu input error: %s", e, exc_info=True)

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

        asyncio.create_task(
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

    async def _handle_number(self, num):
        if self._state == "client":
            clients = sorted(self._tree.keys())
            idx = num - 1
            if 0 <= idx < len(clients):
                self._menu_client = clients[idx]
                await self._show_sites()
            else:
                await self._write("\r\nInvalid choice.\r\n")
                await self._show_clients()
        elif self._state == "site":
            sites = sorted(self._tree[self._menu_client].keys())
            idx = num - 1
            if 0 <= idx < len(sites):
                self._menu_site = sites[idx]
                await self._show_agents()
            else:
                await self._write("\r\nInvalid choice.\r\n")
                await self._show_sites()
        elif self._state == "agent":
            agents = self._tree[self._menu_client][self._menu_site]
            idx = num - 1
            if 0 <= idx < len(agents):
                aid, hostname, ip, status, version, last_seen = agents[idx]
                if status != "online":
                    last_seen_str = ""
                    if last_seen:
                        ago = djangotime.now() - last_seen
                        minutes = int(ago.total_seconds() / 60)
                        if minutes < 1:
                            last_seen_str = "<1m ago"
                        elif minutes < 60:
                            last_seen_str = f"{minutes}m ago"
                        elif minutes < 1440:
                            hours = minutes // 60
                            last_seen_str = f"{hours}h ago"
                        else:
                            days = minutes // 1440
                            last_seen_str = f"{days}d ago"
                    await self._write(
                        f"\r\n\x1b[31m{hostname}\x1b[0m is {status}.\n"
                        f"Last seen: {last_seen_str}\n"
                        "Cannot connect.\r\n"
                    )
                    await self._show_agents()
                    return
                await self._connect_to_agent(aid, hostname)
            else:
                await self._write("\r\nInvalid choice.\r\n")
                await self._show_agents()

    async def _search_agents(self, query):
        query = query.lower()
        matches = []
        for client, sites in self._tree.items():
            for site, agents in sites.items():
                for aid, hostname, ip, status, version, last_seen in agents:
                    if query in hostname.lower():
                        matches.append((client, site, aid, hostname, ip, status, version, last_seen))
        if not matches:
            await self._write(f"\r\nNo agents found matching '{query}'.\r\n")
            await self._show_clients()
            return
        lines = [
            f"\r\n\x1b[1mSearch results for '{query}'\x1b[0m  ({len(matches)} found)",
            "",
        ]
        for i, (client, site, aid, hostname, ip, status, version, last_seen) in enumerate(matches, 1):
            status_color = "\x1b[32m" if status == "online" else "\x1b[31m"
            lines.append(
                f"  {i:>2}. {hostname}  ({client} > {site})\x1b[0m"
                f"  {status_color}{status}\x1b[0m"
            )
        lines += [
            "",
            "  \x1b[2mType number to connect, b to go back\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))
        self._state = "search_results"
        self._search_results = matches

    async def _handle_search_result(self, num):
        idx = num - 1
        if 0 <= idx < len(self._search_results):
            client, site, aid, hostname, ip, status, version, last_seen = self._search_results[idx]
            if status != "online":
                await self._write(
                    f"\r\n\x1b[31m{hostname}\x1b[0m is {status}.\n"
                    "Cannot connect.\r\n"
                )
                await self._show_search_results()
                return
            self._menu_client = client
            self._menu_site = site
            await self._connect_to_agent(aid, hostname)
        else:
            await self._write("\r\nInvalid choice.\r\n")
            await self._show_search_results()

    async def _show_search_results(self):
        matches = self._search_results
        if not matches:
            await self._write("\r\nNo results.\r\n")
            await self._show_clients()
            return
        lines = [
            f"\r\n\x1b[1mSearch results\x1b[0m  ({len(matches)} found)",
            "",
        ]
        for i, (client, site, aid, hostname, ip, status, version, last_seen) in enumerate(matches, 1):
            status_color = "\x1b[32m" if status == "online" else "\x1b[31m"
            lines.append(
                f"  {i:>2}. {hostname}  ({client} > {site})\x1b[0m"
                f"  {status_color}{status}\x1b[0m"
            )
        lines += [
            "",
            "  \x1b[2mType number to connect, b to go back\x1b[0m",
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _show_current(self):
        if self._state == "site":
            await self._show_sites()
        elif self._state == "agent":
            await self._show_agents()
        else:
            await self._show_clients()

    async def _return_from_terminal(self):
        if self._term:
            try:
                await self._term.stop()
            except Exception:
                pass
            self._term = None
        self._state = "agent"
        self._selected_agent = None
        await self._write("\r\n\x1b[33mReturning to agent list...\x1b[0m\r\n")
        await self._show_agents()

    async def _show_help(self):
        lines = [
            "\r\n\x1b[1mTactical RMM SSH Gateway - Help\x1b[0m\r\n",
            "\x1b[2m----------------------------------------\x1b[0m\r\n",
            "",
            "  \x1b[1mNavigation\x1b[0m",
            "    1-9    Select item by number",
            "    b     Back to previous menu",
            "    q     Quit session",
            "    r     Refresh agent list",
            "    ? / h  Show this help",
            "",
            "  \x1b[1mEaster Eggs\x1b[0m",
            "    egg   Start snake game",
            "",
            "  \x1b[1mTerminal\x1b[0m",
            "    Ctrl+^  Return to agent list (from terminal)",
            "    q     Quit terminal",
            "",
            "  \x1b[1mSnake Game\x1b[0m",
            "    WASD or arrow keys  Move",
            "    q     Quit game",
            "",
            "Press any key to continue...\r\n",
        ]
        await self._write("".join(lines))

    async def _idle_check(self):
        timeout = getattr(settings, "SSH_MENU_IDLE_TIMEOUT", 300)
        try:
            while True:
                await asyncio.sleep(15)
                if self._state in ("terminal", "snake", "snake_gameover"):
                    continue
                elapsed = (djangotime.now() - self._last_activity).total_seconds()
                if elapsed >= timeout:
                    await self._write("\r\nIdle timeout. Disconnecting.\r\n")
                    self._chan.exit(0)
                    return
        except asyncio.CancelledError:
            pass
