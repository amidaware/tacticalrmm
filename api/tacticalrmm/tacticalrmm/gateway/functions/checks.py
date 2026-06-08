import asyncio

import asyncssh
from asgiref.sync import sync_to_async
from django.core.cache import cache

from tacticalrmm.constants import AGENT_CHECKS_CACHE_PREFIX
from ..handlers import RejectionHandler
from ..logger import gw_log

C = "\x1b[0m"        # reset
BOLD = "\x1b[1m"     # bold
DIM = "\x1b[2m"      # dim
RED = "\x1b[31m"     # red
GREEN = "\x1b[32m"   # green
YELLOW = "\x1b[33m"  # yellow
BLUE = "\x1b[34m"    # blue
CYAN = "\x1b[36m"    # cyan
WHITE = "\x1b[37m"   # white
BOLD_RED = "\x1b[1;31m"
BOLD_GREEN = "\x1b[1;32m"
BOLD_YELLOW = "\x1b[1;33m"
BOLD_CYAN = "\x1b[1;36m"


class Handler(asyncssh.SSHServerSession):
    name = "checks"

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
        self._done = False

    def connection_made(self, chan):
        self._chan = chan

    def pty_requested(self, term_type, term_size, term_modes):
        return True

    def shell_requested(self):
        asyncio.create_task(self._display_checks())
        return True

    def exec_requested(self, command):
        return RejectionHandler(
            "Check report is interactive only. Type 'checks' in the gateway menu.\r\n",
        )

    def data_received(self, data, datatype):
        if self._done and self._chan and not self._chan.is_closing():
            self._chan.exit(0)

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        pass

    def closed(self):
        pass

    async def _write(self, text=""):
        if self._chan and not self._chan.is_closing():
            self._chan.write(text)

    async def _display_checks(self):
        try:
            tree = await self._build_tree()
            lines = await self._format_tree(tree)
            await self._write("".join(lines))
        except Exception as e:
            gw_log.error("Gateway checks display error: %s", e, exc_info=True)
            await self._write(f"\r\nError loading check data: {e}\r\n")
        self._done = True
        await self._write("\r\nPress any key to close...\r\n")

    async def _build_tree(self):
        from clients.models import Client

        clients = await sync_to_async(
            lambda: list(Client.objects.all().order_by("name"))
        )()
        tree = []
        grand_total = {"failing": 0, "warning": 0, "passing": 0, "total": 0}

        for client in clients:
            sites = await sync_to_async(
                lambda: list(client.sites.all().order_by("name"))
            )()
            client_entry = {"client": client, "sites": [], "failing": 0, "warning": 0, "passing": 0, "total": 0}

            for site in sites:
                agents = await sync_to_async(
                    lambda s=site: list(s.agent_set.all().order_by("hostname"))
                )()
                site_entry = {"site": site, "agents": [], "failing": 0, "warning": 0, "passing": 0, "total": 0}

                for agent in agents:
                    agent_data = await sync_to_async(
                        lambda a=agent: cache.get(f"{AGENT_CHECKS_CACHE_PREFIX}{a.pk}", None)
                    )()
                    if agent_data is None:
                        agent_data = {"failing": 0, "warning": 0, "passing": 0, "total": 0}

                    failing = agent_data.get("failing", 0)
                    warning = agent_data.get("warning", 0)
                    info = agent_data.get("info", 0)
                    passing = agent_data.get("passing", 0)
                    total = agent_data.get("total", 0)

                    status = "online" if agent.status == "online" else "offline"
                    agent_entry = {
                        "hostname": agent.hostname,
                        "agent_id": agent.agent_id,
                        "status": status,
                        "failing": failing + warning + info,
                        "warning": warning,
                        "passing": passing,
                        "total": total,
                    }
                    site_entry["agents"].append(agent_entry)
                    site_entry["failing"] += agent_entry["failing"]
                    site_entry["warning"] += info
                    site_entry["passing"] += passing
                    site_entry["total"] += total

                client_entry["sites"].append(site_entry)
                client_entry["failing"] += site_entry["failing"]
                client_entry["warning"] += site_entry["warning"]
                client_entry["passing"] += site_entry["passing"]
                client_entry["total"] += site_entry["total"]

            tree.append(client_entry)
            grand_total["failing"] += client_entry["failing"]
            grand_total["warning"] += client_entry["warning"]
            grand_total["passing"] += client_entry["passing"]
            grand_total["total"] += client_entry["total"]

        return tree, grand_total

    async def _format_tree(self, data):
        tree, gt = data

        def _count_str(failing, warning, passing, total):
            parts = []
            if failing:
                parts.append(f"{RED}{failing} failed{C}")
            if warning:
                parts.append(f"{YELLOW}{warning} warn{C}")
            parts.append(f"{GREEN}{passing} ok{C}")
            parts.append(f"{DIM}{total} total{C}")
            return "  ".join(parts)

        lines = [
            f"\r\n{BOLD_CYAN}\u2500" * 60 + f"{C}\r\n",
            f"{BOLD_CYAN}  Tactical RMM \u2014 Check Status Report{C}\r\n",
            f"{BOLD_CYAN}\u2500" * 60 + f"{C}\r\n",
            f"{DIM}  Agent checks are cached and refreshed every ~5 min{C}\r\n",
            f"\r\n",
        ]

        for client_entry in tree:
            client = client_entry["client"]
            cf = client_entry["failing"]
            cw = client_entry["warning"]
            cp = client_entry["passing"]
            ct = client_entry["total"]

            cs = f"{RED}{cf} failed{C}" if cf else f"{GREEN}0 failed{C}"
            lines.append(
                f"  {BOLD}{client.name}{C}  {cs}  "
                f"{YELLOW}{cw} warn{C}  "
                f"{GREEN}{cp} ok{C}  "
                f"{DIM}{ct} total{C}\r\n"
            )

            for site_entry in client_entry["sites"]:
                site = site_entry["site"]
                sf = site_entry["failing"]
                sw = site_entry["warning"]
                sp = site_entry["passing"]
                st = site_entry["total"]

                lines.append(
                    f"    {CYAN}{site.name}{C}  "
                    f"{RED if sf else DIM}{sf} failed{C}  "
                    f"{YELLOW if sw else DIM}{sw} warn{C}  "
                    f"{GREEN if sp else DIM}{sp} ok{C}  "
                    f"{DIM}{st} total{C}\r\n"
                )

                for agent_entry in site_entry["agents"]:
                    af = agent_entry["failing"]
                    aw = agent_entry["warning"]
                    ap = agent_entry["passing"]
                    at = agent_entry["total"]
                    status = agent_entry["status"]
                    status_color = GREEN if status == "online" else RED
                    hostname = agent_entry["hostname"]
                    if len(hostname) > 32:
                        hostname = hostname[:29] + "..."

                    lines.append(
                        f"      {status_color}\u25cf{C} {DIM}{hostname}{C}  "
                        f"{RED if af else DIM}{af} failed{C}  "
                        f"{YELLOW if aw else DIM}{aw} warn{C}  "
                        f"{GREEN if ap else DIM}{ap} ok{C}  "
                        f"{DIM}{at} total{C}\r\n"
                    )

            lines.append(f"\r\n")

        lines += [
            f"{BOLD_CYAN}\u2500" * 60 + f"{C}\r\n",
            f"{BOLD}  GLOBAL TOTALS{C}\r\n",
            f"    {BOLD if gt['failing'] else ''}{RED}{gt['failing']} failed{C}  "
            f"{YELLOW}{gt['warning']} warn{C}  "
            f"{GREEN}{gt['passing']} ok{C}  "
            f"{DIM}{gt['total']} total{C}\r\n",
            f"    {DIM}Clients: {len(tree)}  "
            f"Sites: {sum(len(c['sites']) for c in tree)}  "
            f"Agents: {sum(sum(len(s['agents']) for s in c['sites']) for c in tree)}{C}\r\n",
            f"{BOLD_CYAN}\u2500" * 60 + f"{C}\r\n",
        ]

        return lines
