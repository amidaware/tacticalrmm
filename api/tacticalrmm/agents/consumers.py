from agents.models import Agent, AgentHistory
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from tacticalrmm.constants import AGENT_DEFER, AgentHistoryType
from tacticalrmm.permissions import _has_perm_on_agent


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
