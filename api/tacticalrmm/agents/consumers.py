import asyncio
import contextlib
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from packaging import version as pyver

from agents.models import Agent, AgentHistory
from logs.models import AuditLog
from tacticalrmm.constants import (
    AgentHistoryType,
    AuditActionType,
    AuditObjType,
)
from tacticalrmm.permissions import _has_perm_on_agent

# Shared across all CommandStreamConsumer instances
active_streams = {}


class CommandStreamConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.stop_evt = None
        self.agent_id = None
        self.group_name = None
        self.cmd_id = None
        self.authorized = False

    async def connect(self):
        """Handle websocket connection."""
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        if not self.user.is_authenticated:
            await self.close(4401)
            return

        if self.user.block_dashboard_login:
            await self.close()
            return

        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        has_permission = await self.has_perm(self.agent_id)
        if not has_permission:
            await self.accept()
            await self.send_json(
                {
                    "error": "You do not have permission to perform this action.",
                    "status": 403,
                }
            )
            await self.close(code=4003)
            return

        agent = await self.get_agent(self.agent_id)
        if pyver.parse(agent.version) < pyver.parse("2.10.0"):
            await self.accept()
            await self.send_json(
                {
                    "error": "The streaming feature requires agent version 2.10.0 or higher.",
                    "status": 400,
                }
            )
            await self.close()
            return

        # Don’t create a group yet, cmd_id not known
        await self.accept()
        self.authorized = True

    async def disconnect(self, close_code):
        """Cleanup on disconnect."""
        chan = self.channel_name

        if chan in active_streams:
            cmd_streams = active_streams[chan]
            if self.cmd_id in cmd_streams:
                stop_evt, stream_task = cmd_streams.pop(self.cmd_id, (None, None))
                if stop_evt:
                    stop_evt.set()
                if stream_task and not stream_task.done():
                    with contextlib.suppress(asyncio.CancelledError):
                        await stream_task
            if not cmd_streams:
                active_streams.pop(chan)

        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not getattr(self, "authorized", False):
            await self.close(4403)
            return

        agent = await self.get_agent(self.agent_id)
        try:
            cmd = content["cmd"]
            shell = content.get("shell") or "cmd"
            custom_shell = content.get("custom_shell")
            run_as_user = bool(content.get("run_as_user", False))
            timeout = int(content.get("timeout", 30))
        except (KeyError, ValueError, TypeError):
            await self.send_json({"error": "Invalid command payload"})
            return

        shell = custom_shell if shell == "custom" and custom_shell else shell
        cmd_id = content.get("cmd_id") or uuid.uuid4().hex
        self.cmd_id = cmd_id

        # Create per-session group now that cmd_id is known
        self.group_name = f"agent_cmd_{self.agent_id}_{cmd_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.send_json({"cmd_id": cmd_id})
        subject_output = f"{self.agent_id}.cmdoutput.{cmd_id}"

        hist = await AgentHistory.objects.acreate(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=self.user.username[:50],
        )

        await AuditLog.objects.acreate(
            username=self.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{self.user.username} issued {shell} command on {agent.hostname}.",
            after_value=cmd,
            debug_info={
                "ip": self.scope.get("client")[0] if self.scope.get("client") else ""
            },
        )

        chan = self.channel_name
        if chan not in active_streams:
            active_streams[chan] = {}

        data = {
            "func": "rawcmd",
            "timeout": timeout,
            "stream": True,
            "payload": {"command": cmd, "shell": shell, "cmd_id": cmd_id},
            "run_as_user": run_as_user,
            "id": hist.pk,
        }

        self.stop_evt = asyncio.Event()
        self.stream_task = asyncio.create_task(
            agent.nats_stream_cmd(
                data,
                timeout=timeout + 2,
                stop_evt=self.stop_evt,
                output_subject=subject_output,
                group=self.group_name,
            )
        )
        active_streams[chan][cmd_id] = (self.stop_evt, self.stream_task)

    async def stream_output(self, event):
        await self.send_json(
            {
                k: v
                for k, v in event.items()
                if k in ("output", "done", "exit_code", "cmd_id")
            }
        )

    async def has_perm(self, agent_id: str) -> bool:
        return await database_sync_to_async(self._has_perm_on_agent)(agent_id)

    async def get_agent(self, agent_id: str):
        return await Agent.objects.aget(agent_id=agent_id)

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)

    def _has_perm_on_agent(self, agent_id: str) -> bool:
        return self._has_perm("can_send_cmd") and _has_perm_on_agent(
            self.user, agent_id
        )
