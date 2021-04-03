import asyncio
import json

from django.contrib.auth.models import AnonymousUser
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from agents.models import Agent
from accounts.models import User


class DashInfo(AsyncWebsocketConsumer):
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

    async def receive(self, text_data=None, bytes_data=None):
        pass

    @database_sync_to_async
    def get_dashboard_info(self):
        server_offline_count = len(
            [
                agent
                for agent in Agent.objects.filter(monitoring_type="server").only(
                    "pk",
                    "last_seen",
                    "overdue_time",
                    "offline_time",
                )
                if not agent.status == "online"
            ]
        )

        workstation_offline_count = len(
            [
                agent
                for agent in Agent.objects.filter(monitoring_type="workstation").only(
                    "pk",
                    "last_seen",
                    "overdue_time",
                    "offline_time",
                )
                if not agent.status == "online"
            ]
        )

        user = User.objects.get(pk=self.user.pk)

        ret = {
            "trmm_version": settings.TRMM_VERSION,
            "client_tree_sort": user.client_tree_sort,
            "default_agent_tbl_tab": user.default_agent_tbl_tab,
            "dbl_click_action": user.agent_dblclick_action,
            "dark_mode": user.dark_mode,
            "show_community_scripts": user.show_community_scripts,
            "total_server_offline_count": server_offline_count,
            "total_workstation_offline_count": workstation_offline_count,
            "total_server_count": Agent.objects.filter(
                monitoring_type="server"
            ).count(),
            "total_workstation_count": Agent.objects.filter(
                monitoring_type="workstation"
            ).count(),
        }
        return json.dumps(ret)

    async def send_dash_info(self):
        while self.connected:
            c = await self.get_dashboard_info()
            await self.send(c)
            await asyncio.sleep(1)
