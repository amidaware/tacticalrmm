import asyncio

from agents.models import Agent
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class DashInfo(AsyncJsonWebsocketConsumer):
    async def connect(self):

        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()

        await self.accept()
        self.connected = True
        self.dash_info = asyncio.create_task(self.send_dash_info())

    async def disconnect(self, close_code):

        try:
            self.dash_info.cancel()
        except:
            pass

        self.connected = False
        await self.close()

    async def receive(self, json_data=None):
        pass

    @database_sync_to_async
    def get_dashboard_info(self):
        total_agents = Agent.objects.filter_by_role(self.user).only(
            "pk",
            "last_seen",
            "overdue_time",
            "offline_time",
        )

        server_offline_count = len(
            [
                agent
                for agent in total_agents
                if agent.monitoring_type == "server" and agent.status != "online"
            ]
        )

        workstation_offline_count = len(
            [
                agent
                for agent in total_agents
                if agent.monitoring_type == "workstation" and agent.status != "online"
            ]
        )

        ret = {
            "total_server_offline_count": server_offline_count,
            "total_workstation_offline_count": workstation_offline_count,
            "total_server_count": len(
                [agent for agent in total_agents if agent.monitoring_type == "server"]
            ),
            "total_workstation_count": len(
                [
                    agent
                    for agent in total_agents
                    if agent.monitoring_type == "workstation"
                ]
            ),
        }
        return ret

    async def send_dash_info(self):
        while self.connected:
            c = await self.get_dashboard_info()
            await self.send_json(c)
            await asyncio.sleep(30)
