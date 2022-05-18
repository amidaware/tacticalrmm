import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.utils import timezone as djangotime

from agents.models import Agent
from tacticalrmm.constants import AgentMonType


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
            "total_server_offline_count": offline_server_agents_count,
            "total_workstation_offline_count": offline_workstation_agents_count,
            "total_server_count": total_server_agents_count,
            "total_workstation_count": total_workstation_agents_count,
        }

    async def send_dash_info(self):
        while self.connected:
            c = await self.get_dashboard_info()
            await self.send_json(c)
            await asyncio.sleep(30)
