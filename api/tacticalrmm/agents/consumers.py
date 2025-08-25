from agents.models import Agent, AgentHistory
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from tacticalrmm.constants import AGENT_DEFER, AgentHistoryType
from tacticalrmm.permissions import _has_perm_on_agent
import asyncio, contextlib
import uuid
from logs.models import AuditLog

# Shared across all CommandStreamConsumer instances
active_streams = {}
stream_buffers = {}


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
        self.cmd_id = None

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

        if chan in stream_buffers:
            stream_buffers[chan].pop(self.cmd_id, None)
            if not stream_buffers[chan]:
                stream_buffers.pop(chan)

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
        cmd_id = content.get("cmd_id") or uuid.uuid4().hex
        self.cmd_id = cmd_id
        await self.send_json({"cmd_id": cmd_id})
        subject_output = f"{self.agent_id}.cmdoutput.{cmd_id}"

        hist = await database_sync_to_async(AgentHistory.objects.create)(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=self.user.username[:50],
        )

        await database_sync_to_async(AuditLog.audit_raw_command)(
            username=self.user.username,
            agent=agent,
            cmd=cmd,
            shell=shell,
            debug_info={"ip": self.scope.get("client")[0] if self.scope.get("client") else ""},
        )

        chan = self.channel_name

        if chan not in stream_buffers:
            stream_buffers[chan] = {}
        stream_buffers[chan][cmd_id] = {
            "lines": [],
            "hist_id": hist.pk,
        }

        data = {
            "func": "rawcmd",
            "timeout": timeout,
            "stream": True,
            "payload": {"command": cmd, "shell": shell, "cmd_id": cmd_id},
            "run_as_user": run_as_user,
        }

        if chan not in active_streams:
            active_streams[chan] = {}

        self.stop_evt = asyncio.Event()
        self.stream_task = asyncio.create_task(
            agent.nats_stream_cmd(data, timeout=timeout + 2, stop_evt=self.stop_evt, output_subject=subject_output)
        )
        active_streams[chan][cmd_id] = (self.stop_evt, self.stream_task)

    async def stream_output(self, event):
        cmd_id = event.get("cmd_id")
        chan = self.channel_name

        agent_buffers = stream_buffers.get(chan, {})
        stream_entry = agent_buffers.get(cmd_id)

        if stream_entry is None:
            # todo: need to check this none type
            # if not event.get("done"):
                # print(f"No stream buffer found for channel={chan} cmd_id={cmd_id}")
            return
        if "output" in event:
            stream_entry["lines"].append(event["output"])
        if event.get("done") is True:
            full_output = "\n".join(stream_entry["lines"])
            hist_id = stream_entry["hist_id"]
            await database_sync_to_async(AgentHistory.objects.filter(pk=hist_id).update)(
                results=full_output,
            )
            agent_buffers.pop(cmd_id, None)
            if not agent_buffers:
                stream_buffers.pop(chan, None)
        await self.send_json({
            k: v for k, v in event.items()
            if k in ("output", "done", "exit_code", "cmd_id")
        })

    @database_sync_to_async
    def has_perm(self, agent_id: str) -> bool:
        return self._has_perm("can_send_cmd") and _has_perm_on_agent(self.user, agent_id)

    @database_sync_to_async
    def get_agent(self, agent_id: str):
        return get_object_or_404(Agent, agent_id=agent_id)

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (self.user.role and getattr(self.user.role, "is_superuser")):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)