import asyncio
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import threading
import uuid
from contextlib import suppress

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, JsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.utils import timezone as djangotime

from agents.models import Agent
from core.models import CoreSettings
from tacticalrmm.constants import AgentMonType
from tacticalrmm.helpers import days_until_cert_expires
from tacticalrmm.logger import logger


def _has_perm(user, perm: str) -> bool:
    if user.is_superuser or (user.role and getattr(user.role, "is_superuser")):
        return True

    # make sure non-superusers with empty roles aren't permitted
    elif not user.role:
        return False

    return user.role and getattr(user.role, perm)


class DashInfo(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        if self.user.block_dashboard_login:
            await self.close()
            return

        await self.accept()
        self.connected = True
        self.dash_info = asyncio.create_task(self.send_dash_info())

    async def disconnect(self, close_code):
        with suppress(Exception):
            self.dash_info.cancel()

        self.connected = False

    async def receive_json(self, payload, **kwargs):
        pass

    @database_sync_to_async
    def get_dashboard_info(self):
        total_server_agents_count = (
            Agent.objects.filter_by_role(self.user)
            .filter(monitoring_type=AgentMonType.SERVER)
            .count()
        )
        offline_server_agents_count = (
            Agent.objects.filter_by_role(self.user)
            .filter(monitoring_type=AgentMonType.SERVER)
            .filter(
                last_seen__lt=djangotime.now()
                - (djangotime.timedelta(minutes=1) * F("offline_time"))
            )
            .count()
        )
        total_workstation_agents_count = (
            Agent.objects.filter_by_role(self.user)
            .filter(monitoring_type=AgentMonType.WORKSTATION)
            .count()
        )
        offline_workstation_agents_count = (
            Agent.objects.filter_by_role(self.user)
            .filter(monitoring_type=AgentMonType.WORKSTATION)
            .filter(
                last_seen__lt=djangotime.now()
                - (djangotime.timedelta(minutes=1) * F("offline_time"))
            )
            .count()
        )
        return {
            "action": "dashboard.agentcount",
            "data": {
                "total_server_offline_count": offline_server_agents_count,
                "total_workstation_offline_count": offline_workstation_agents_count,
                "total_server_count": total_server_agents_count,
                "total_workstation_count": total_workstation_agents_count,
                "days_until_cert_expires": days_until_cert_expires(),
            },
        }

    async def send_dash_info(self):
        while self.connected:
            c = await self.get_dashboard_info()
            await self.send_json(c)
            await asyncio.sleep(30)


class TerminalConsumer(JsonWebsocketConsumer):
    child_pid = None
    fd = None
    shell = None
    command = ["/bin/bash"]
    user = None
    subprocess = None
    authorized = False
    connected = False

    def run_command(self):
        master_fd, slave_fd = pty.openpty()

        self.fd = master_fd
        env = os.environ.copy()
        env["TERM"] = "xterm"

        with subprocess.Popen(  # pylint: disable=subprocess-popen-preexec-fn
            self.command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            env=env,
            cwd=os.getenv("HOME", os.getcwd()),
        ) as proc:
            self.subprocess = proc
            self.child_pid = proc.pid
            proc.wait()

            # Subprocess has finished, close the websocket
            # happens when process exits, either via user exiting using exit() or by error
            self.subprocess = None
            self.child_pid = None
            if self.connected:
                self.connected = False
                self.close(4030)

    def connect(self):
        if "user" not in self.scope:
            self.close(4401)
            return

        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            self.close()
            return

        if not self.user.is_authenticated:
            self.close(4401)
            return

        core: CoreSettings = CoreSettings.objects.first()  # type: ignore
        if not core.web_terminal_enabled:
            self.close(4401)
            return

        if self.user.block_dashboard_login or not _has_perm(
            self.user, "can_use_webterm"
        ):
            self.close(4401)
            return

        if self.child_pid is not None:
            return

        self.connected = True
        self.authorized = True
        self.accept()

        # Daemonize the thread so it automatically dies when the main thread exits
        thread = threading.Thread(target=self.run_command, daemon=True)
        thread.start()

        thread = threading.Thread(target=self.read_from_pty, daemon=True)
        thread.start()

    def read_from_pty(self):
        while True:
            select.select([self.fd], [], [])
            output = os.read(self.fd, 1024)
            if not output:
                break
            message = output.decode(errors="ignore")
            self.send_json(
                {
                    "action": "trmmcli.output",
                    "data": {"output": message, "messageId": str(uuid.uuid4())},
                }
            )

    def resize(self, row, col, xpix=0, ypix=0):
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    def write_to_pty(self, message):
        os.write(self.fd, message.encode())

    def kill_pty(self):
        if self.subprocess is not None:
            try:
                os.killpg(os.getpgid(self.child_pid), signal.SIGKILL)
            except Exception as e:
                logger.error(f"Failed to kill process group: {str(e)}")
            finally:
                self.subprocess = None
                self.child_pid = None

    def disconnect(self, code):
        self.connected = False
        self.kill_pty()

    def receive_json(self, data):
        if not self.authorized:
            return

        action = data.get("action", None)

        if not action:
            return

        if action == "trmmcli.resize":
            self.resize(data["data"]["rows"], data["data"]["cols"])
        elif action == "trmmcli.input":
            message = data["data"]["input"]
            self.write_to_pty(message)
        elif action == "trmmcli.disconnect":
            self.kill_pty()
            self.send_json(
                {"action": "trmmcli.output", "data": {"output": "Terminal killed!"}}
            )
