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
            (a.agent_id, a.hostname, a.public_ip or "", a.status)
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
        self._snake_buf = ""

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
                    self._handle_snake_input(ch)
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

    async def _handle_char(self, ch):
        try:
            self._last_activity = djangotime.now()

            if ch in ("\r", "\n"):
                if self._buf:
                    cmd = self._buf.strip().lower()
                    self._buf = ""
                    if cmd == "egg":
                        await self._start_snake()
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

            if ch.isdigit():
                try:
                    num = int(ch)
                    await self._handle_number(num)
                except ValueError:
                    pass
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
                await self._write("\r\nInvalid choice.\r\n")
                await self._show_agents()

    async def _show_current(self):
        if self._state == "site":
            await self._show_sites()
        elif self._state == "agent":
            await self._show_agents()
        else:
            await self._show_clients()

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

    async def _start_snake(self):
        self._state = "snake"
        self._snake_width = 40
        self._snake_height = 16
        mid_r = self._snake_height // 2
        mid_c = self._snake_width // 2
        self._snake_body = [(mid_r, c) for c in range(mid_c, mid_c - 3, -1)]
        self._snake_dir = (0, 1)
        self._snake_score = 0
        self._snake_buf = ""
        self._snake_food = self._snake_place_food()
        await self._write("\x1b[2J\x1b[H")
        await self._draw_snake()
        asyncio.create_task(self._snake_loop())

    def _snake_place_food(self):
        occupied = set(self._snake_body)
        free = self._snake_height * self._snake_width - len(occupied)
        if free <= 0:
            return None
        for _ in range(100):
            r = random.randrange(self._snake_height)
            c = random.randrange(self._snake_width)
            if (r, c) not in occupied:
                return (r, c)
        for r in range(self._snake_height):
            for c in range(self._snake_width):
                if (r, c) not in occupied:
                    return (r, c)
        return None

    async def _draw_snake(self):
        lines = ["\x1b[H"]
        lines.append(
            f"Score: {self._snake_score}    (WASD move, Q quit)\r\n"
        )
        for r in range(self._snake_height):
            for c in range(self._snake_width):
                if (r, c) == self._snake_body[0]:
                    lines.append("\x1b[32mO\x1b[0m")
                elif (r, c) in self._snake_body:
                    lines.append("o")
                elif self._snake_food and (r, c) == self._snake_food:
                    lines.append("\x1b[33m@\x1b[0m")
                else:
                    lines.append(".")
            lines.append("\r\n")
        lines.append("\x1b[J")
        await self._write("".join(lines))

    async def _snake_loop(self):
        try:
            while self._state == "snake":
                await asyncio.sleep(0.15)
                if self._state != "snake":
                    return
                head = self._snake_body[0]
                dr, dc = self._snake_dir
                new_head = (head[0] + dr, head[1] + dc)

                if not (0 <= new_head[0] < self._snake_height and 0 <= new_head[1] < self._snake_width):
                    await self._snake_game_over()
                    return

                if new_head in self._snake_body:
                    await self._snake_game_over()
                    return

                self._snake_body.insert(0, new_head)

                if new_head == self._snake_food:
                    self._snake_score += 1
                    self._snake_food = self._snake_place_food()
                    if self._snake_food is None:
                        await self._snake_win()
                        return
                else:
                    self._snake_body.pop()

                await self._draw_snake()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("SSH snake loop error: %s", e, exc_info=True)

    async def _snake_game_over(self):
        scores = _add_highscore(self._user.username, self._snake_score, False)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[31mGame Over!\x1b[0m\r\n",
            f"Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to return to menu...\r\n",
        ]
        await self._write("".join(lines))
        self._state = "snake_gameover"

    async def _snake_win(self):
        scores = _add_highscore(self._user.username, self._snake_score, True)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[32mYou Win!\x1b[0m\r\n",
            f"Final Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to return to menu...\r\n",
        ]
        await self._write("".join(lines))
        self._state = "snake_gameover"

    def _handle_snake_input(self, ch):
        if ch.lower() == "q" or ch == "\x03":
            asyncio.create_task(self._snake_quit())
            return
        dirs = {"w": (-1, 0), "s": (1, 0), "a": (0, -1), "d": (0, 1)}
        if ch.lower() in dirs:
            dr, dc = dirs[ch.lower()]
            if (dr, dc) != (-self._snake_dir[0], -self._snake_dir[1]):
                self._snake_dir = (dr, dc)
            return
        self._snake_buf += ch
        if len(self._snake_buf) > 10:
            self._snake_buf = self._snake_buf[-5:]
        for seq, dr, dc in [
            ("\x1b[A", -1, 0), ("\x1b[B", 1, 0),
            ("\x1b[C", 0, 1), ("\x1b[D", 0, -1),
        ]:
            if seq in self._snake_buf:
                self._snake_buf = ""
                if (dr, dc) != (-self._snake_dir[0], -self._snake_dir[1]):
                    self._snake_dir = (dr, dc)
                return

    async def _snake_quit(self):
        self._state = "client"
        self._snake_buf = ""
        await self._show_clients()
