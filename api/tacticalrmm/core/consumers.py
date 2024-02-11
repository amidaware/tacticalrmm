import asyncio
import os
from contextlib import suppress

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.utils import timezone as djangotime

from agents.models import Agent
from tacticalrmm.constants import AgentMonType
from tacticalrmm.helpers import days_until_cert_expires
from .utils import get_crontab_job

class DashInfo(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()

        await self.accept()
        self.connected = True
        self.dash_info = asyncio.create_task(self.send_dash_info())

    async def disconnect(self, close_code):
        with suppress(Exception):
            self.dash_info.cancel()

        self.connected = False

    async def receive_json(self, payload, **kwargs):
        # trmm cli
        if payload["action"] == "trmmcli.connect":
            await self.connect_trmm_cli(payload["data"])
        elif payload["action"] == "trmmcli.input":
            await self.input_trmm_cli(payload["data"])
        elif payload["action"] == "trmmcli.resize":
            await self.resize_trmm_cli(payload["data"])
        elif payload["action"] == "trmmcli.disconnect":
            await self.disconnect_trmm_cli()

        # server tasks
        elif payload["action"] == "core.server.getcron":
            await self.send_crontab_config()


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
            "action": "dashinfo",
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

    # trmm cli
    def set_winsize(self, fd, row, col, xpix=0, ypix=0):
        import struct, termios, fcntl

        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    fd = None
    child_pid = None

    async def read_and_forward_pty_output(self):
        import select

        max_read_bytes = 1024 * 20
        while True:
            await asyncio.sleep(0.01)
            if self.fd:
                timeout_sec = 0
                (data_ready, _, _) = select.select([self.fd], [], [], timeout_sec)
                if data_ready:
                    output = os.read(self.fd, max_read_bytes).decode(errors="ignore")
                    await self.send_json(
                        {"action": "trmmcli.output", "data": {"output": output}}
                    )

    async def connect_trmm_cli(self, payload):
        import pty, subprocess

        if self.child_pid:
            # already started child process, don't start another
            return

        # create child process attached to a pty we can read from and write to
        (child_pid, fd) = pty.fork()
        if child_pid == 0:
            # this is the child process fork.
            # anything printed here will show up in the pty, including the output
            # of this subprocess
            subprocess.run("bash")
        else:
            # this is the parent process fork.
            # store child fd and pid
            self.fd = fd
            self.child_pid = child_pid
            self.set_winsize(self.fd, payload["rows"], payload["cols"])
            asyncio.create_task(self.read_and_forward_pty_output())

    async def input_trmm_cli(self, payload):
        if not self.fd:
            await self.connect_trmm_cli()

        os.write(self.fd, payload["input"].encode())

    async def resize_trmm_cli(self, payload):
        self.set_winsize(self.fd, payload["rows"], payload["cols"])

    async def disconnect_trmm_cli(self):
        if self.fd:
            os.close(self.fd)
            self.fd = None
            self.child_pid = None

    # trmm cron
    async def send_crontab_config(self):
        
        proc = await asyncio.create_subprocess_exec(
        'crontab','-l',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        print(stdout, stderr)
        await self.send_json({
            "action": "core.server.getcron",
            "data": f"{stdout.decode()}\n{stderr.decode()}"
        })
