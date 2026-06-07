import asyncio

import asyncssh
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone as djangotime

from ..audit import _close_session_and_audit, _record_session_and_audit
from ..logger import gw_log
from ..terminal import TerminalProxy
from ..utils import _get_user_group, _resolve_and_check

TRMM_LOGO = """@@@@@@@@@
    @@@@      @@@@
   @@@          @@@
  @@* @@@@@@@@@@ @@@
  @@      @@      @@
  @@    @ @@ @    @@
  @@.  @@ @@ @@  @@@
   @@@ @@ @@ @@ @@@
    @@@@@ @@ @@@@@
      @@@@@@@@@@"""


@sync_to_async
def _get_menu_agents(user):
    from agents.models import Agent
    agents = Agent.objects.select_related("site__client").only(
        "agent_id", "hostname", "public_ip", "last_seen", "version", "notes",
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


class MenuSessionHandler(asyncssh.SSHServerSession):
    name = "menu"

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
        self._agent_page = 0
        self._agents_per_page = 10
        self._active_func = None

    def connection_made(self, chan):
        self._chan = chan
        self._started_at = djangotime.now()
        self._state = "connected"

    def shell_requested(self):
        self._state = "menu"
        asyncio.create_task(self._enter_menu())
        asyncio.create_task(self._idle_check())
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
        self._state = "exec"
        self._exec_command = command
        return True

    def data_received(self, data, datatype):
        try:
            if self._active_func:
                if isinstance(data, bytes):
                    text = data.decode("utf-8", errors="replace")
                else:
                    text = data
                for ch in text:
                    self._active_func.handle_input(ch)
                return
            if self._state == "terminal":
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
            if self._state == "exec":
                if isinstance(data, bytes):
                    self._chan.write(data)
                else:
                    self._chan.write(data.encode('utf-8') if isinstance(data, str) else data)
                return
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="replace")
            else:
                text = data
            if self._state == "snake_gameover":
                self._state = "client"
                asyncio.create_task(self._show_clients())
                return
            for ch in text:
                asyncio.create_task(self._handle_char(ch))
        except Exception as e:
            gw_log.error("Gateway menu data_received error: %s", e, exc_info=True)

    def connection_lost(self, exc):
        if self._term:
            asyncio.create_task(self._term.stop())
        if exc:
            gw_log.error("Gateway menu connection lost: %s", exc)

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
        gw_log.info(
            "Gateway menu session started user=%s remote_ip=%s",
            self._user.username, self._remote_ip,
        )
        await self._show_clients()

    async def _show_clients(self):
        self._state = "client"
        clients = sorted(self._tree.keys())
        logo_lines = TRMM_LOGO.split("\n")
        lines = [""]
        for l in logo_lines:
            lines.append(f"\x1b[36m{l}\x1b[0m")
        lines += [
            f"\x1b[1mTactical RMM Gateway\x1b[0m \x1b[2mv{settings.TRMM_VERSION}\x1b[0m",
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
        total_agents = len(agents)
        total_pages = max(1, (total_agents + self._agents_per_page - 1) // self._agents_per_page)
        if self._agent_page >= total_pages:
            self._agent_page = total_pages - 1
        start_idx = self._agent_page * self._agents_per_page
        end_idx = min(start_idx + self._agents_per_page, total_agents)
        page_agents = agents[start_idx:end_idx]

        lines = [
            f"\r\n\x1b[1mClients \x1b[2m>\x1b[0m {self._menu_client} \x1b[2m>\x1b[0m {self._menu_site}\x1b[0m",
            f"\x1b[2mSelect an agent\x1b[0m \x1b[33m(Page {self._agent_page + 1} of {total_pages})\x1b[0m",
            "",
        ]
        for i, (aid, hostname, ip, status, version, last_seen) in enumerate(page_agents, start_idx + 1):
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
        nav_hints = []
        if total_pages > 1:
            nav_hints.append("\x1b[2m n. Next page\x1b[0m")
            nav_hints.append("\x1b[2m p. Prev page\x1b[0m")
        lines += [
            "",
            "  \x1b[2m b. Back\x1b[0m   \x1b[2m r. Refresh\x1b[0m   \x1b[2m q. Quit\x1b[0m" +
            ("   " + "   ".join(nav_hints) if nav_hints else ""),
            "",
            "Enter choice: ",
        ]
        await self._write("\r\n".join(lines))

    async def _handle_char(self, ch):
        try:
            self._last_activity = djangotime.now()

            if ch in ("\r", "\n"):
                if self._state == "search":
                    if self._buf.strip():
                        query = self._buf.strip()
                        self._buf = ""
                        await self._search_agents(query)
                    return
                if self._buf.strip().isdigit():
                    num = int(self._buf.strip())
                    self._buf = ""
                    if self._state == "search_results":
                        await self._handle_search_result(num)
                    else:
                        await self._handle_number(num)
                    return
                if self._buf:
                    cmd = self._buf.strip().lower()
                    self._buf = ""
                    if cmd:
                        await self._try_launch_function(cmd)
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

            if ch in ("n", "N") and self._state == "agent":
                agents = self._tree[self._menu_client][self._menu_site]
                total_pages = max(1, (len(agents) + self._agents_per_page - 1) // self._agents_per_page)
                if self._agent_page < total_pages - 1:
                    self._agent_page += 1
                    await self._show_agents()
                return

            if ch in ("p", "P") and self._state == "agent":
                if self._agent_page > 0:
                    self._agent_page -= 1
                    await self._show_agents()
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
            gw_log.error("Gateway menu input error: %s", e, exc_info=True)

    async def _try_launch_function(self, cmd):
        from . import FUNCTION_REGISTRY
        func_cls = FUNCTION_REGISTRY.get(cmd.lower())
        if func_cls is None:
            await self._write(f"\r\nUnknown command: {cmd}\r\n")
            await self._show_current()
            return
        if hasattr(func_cls, "launch") and callable(func_cls.launch):
            child = await func_cls.launch(self)
            if child:
                self._active_func = child
        else:
            await self._write(f"\r\nFunction '{cmd}' not available in menu.\r\n")
            await self._show_current()

    async def _connect_to_agent(self, agent_id, hostname):
        from agents.models import Agent

        agent = await _resolve_and_check(self._user, agent_id)
        if agent is None:
            await self._write(
                f"\r\n\x1b[31mAccess denied: you don't have permission "
                f"to access agent {hostname}\x1b[0m\r\n"
            )
            return

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
        self._term = TerminalProxy(agent, self._session_id, shell)

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
        gw_log.info(
            "Gateway menu: user=%s connected to agent=%s hostname=%s",
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
                gw_log.error("Gateway menu output_cb error", exc_info=True)

        try:
            await self._term.start(output_cb)
        except Exception as e:
            gw_log.error("Gateway menu: failed to start terminal: %s", e, exc_info=True)
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
                self._agent_page = 0
                await self._show_agents()
            else:
                await self._write("\r\nInvalid choice.\r\n")
                await self._show_sites()
        elif self._state == "agent":
            agents = self._tree[self._menu_client][self._menu_site]
            total_agents = len(agents)
            total_pages = max(1, (len(agents) + self._agents_per_page - 1) // self._agents_per_page)
            if self._agent_page >= total_pages:
                self._agent_page = total_pages - 1
            start_idx = self._agent_page * self._agents_per_page
            end_idx = min(start_idx + self._agents_per_page, total_agents)
            idx = num - 1
            actual_idx = start_idx + idx
            if start_idx <= actual_idx < end_idx:
                aid, hostname, ip, status, version, last_seen = agents[actual_idx]
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
        from . import FUNCTION_REGISTRY
        func_names = sorted(k for k in FUNCTION_REGISTRY if k != "menu")
        lines = [
            "\r\n\x1b[1mTactical RMM Gateway - Help\x1b[0m\r\n",
            "\x1b[2m----------------------------------------\x1b[0m\r\n",
            "",
            "  \x1b[1mNavigation\x1b[0m",
            "    1-9    Select item by number",
            "    b     Back to previous menu",
            "    q     Quit session",
            "    r     Refresh agent list",
            "    ? / h  Show this help",
            "",
        ]
        if func_names:
            lines.append("  \x1b[1mFunctions\x1b[0m")
            for fn in func_names:
                lines.append(f"    {fn}")
            lines.append("")
        lines += [
            "  \x1b[1mTerminal\x1b[0m",
            "    Ctrl+^  Return to agent list (from terminal)",
            "    q     Quit terminal",
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


async def go_back(handler):
    handler._state = "client"
    await handler._show_clients()
