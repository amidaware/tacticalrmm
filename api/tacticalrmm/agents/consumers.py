from agents.models import Agent, AgentHistory
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from tacticalrmm.constants import AGENT_DEFER, AgentHistoryType
from tacticalrmm.permissions import _has_perm_on_agent
import asyncio, contextlib
import uuid

# Shared across all CommandStreamConsumer instances
active_streams = {}


class SendCMD(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()

        await self.accept()

    async def receive_json(self, payload, **kwargs):
        auth = await self.has_perm(payload["agent_id"])
        if not auth:
            await self.send_json(
                {"ret": "You do not have permission to perform this action."}
            )
            return

        agent = await self.get_agent(payload["agent_id"])
        timeout = int(payload["timeout"])
        if payload["shell"] == "custom" and payload["custom_shell"]:
            shell = payload["custom_shell"]
        else:
            shell = payload["shell"]

        hist_pk = await self.get_history_id(agent, payload["cmd"])

        data = {
            "func": "rawcmd",
            "timeout": timeout,
            "payload": {
                "command": payload["cmd"],
                "shell": shell,
            },
            "id": hist_pk,
        }

        ret = await agent.nats_cmd(data, timeout=timeout + 2)
        await self.send_json({"ret": ret})

    async def disconnect(self, _):
        pass

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True

        # make sure non-superusers with empty roles aren't permitted
        elif not self.user.role:
            return False

        return self.user.role and getattr(self.user.role, perm)

    @database_sync_to_async  # type: ignore
    def get_agent(self, agent_id: str) -> "Agent":
        return get_object_or_404(Agent.objects.defer(*AGENT_DEFER), agent_id=agent_id)

    @database_sync_to_async  # type: ignore
    def get_history_id(self, agent: "Agent", cmd: str) -> int:
        hist = AgentHistory.objects.create(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=self.user.username[:50],
        )
        return hist.pk

    @database_sync_to_async  # type: ignore
    def has_perm(self, agent_id: str) -> bool:
        return self._has_perm("can_send_cmd") and _has_perm_on_agent(
            self.user, agent_id
        )

class CommandStreamConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.stop_evt = None
        self.agent_id = None
        self.group_name = None

    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        self.group_name = f"agent_cmd_{self.agent_id}"

        has_permission = await self.has_perm(self.agent_id)
        if not has_permission:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Only stop if this connection owns the active stream
        if active_streams.get(self.agent_id) == (self.stop_evt, self.stream_task):
            active_streams.pop(self.agent_id, None)

            if self.stream_task and not self.stream_task.done():
                if self.stop_evt:
                    self.stop_evt.set()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.stream_task

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
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

        # Generate a unique subject for this command
        cmd_id = uuid.uuid4().hex
        subject_output = f"{self.agent_id}.cmdoutput.{cmd_id}"

        data = {
            "func": "rawcmd",
            "timeout": timeout,
            "stream": True,
            "payload": {"command": cmd, "shell": shell, "cmd_id": cmd_id},
            "run_as_user": run_as_user,
        }

        # cancel any previous stream for this socket before starting a new one
        prev = active_streams.get(self.agent_id)
        if prev:
            prev_evt, prev_task = prev
            if prev_evt:
                prev_evt.set()
            if prev_task and not prev_task.done():
                with contextlib.suppress(asyncio.CancelledError):
                    await prev_task

        self.stop_evt = asyncio.Event()
        self.stream_task = asyncio.create_task(
            agent.nats_stream_cmd(data, timeout=timeout + 2, stop_evt=self.stop_evt, output_subject=subject_output)
        )
        active_streams[self.agent_id] = (self.stop_evt, self.stream_task)
    async def stream_output(self, event):
        # pass through anything we got (output/done/exit_code)
        await self.send_json({k: v for k, v in event.items() if k in ("output","done","exit_code")})

    @database_sync_to_async
    def has_perm(self, agent_id: str) -> bool:
        return self._has_perm("can_send_cmd") and _has_perm_on_agent(
            self.user, agent_id
        )

    @database_sync_to_async
    def get_agent(self, agent_id: str):
        return get_object_or_404(Agent, agent_id=agent_id)

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)