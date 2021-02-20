import asyncio
import json

import websockets
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import CoreSettings

from .helpers import get_auth_token


class Command(BaseCommand):
    help = "Sets up initial mesh central configuration"

    async def websocket_call(self, mesh_settings):
        token = get_auth_token(mesh_settings.mesh_username, mesh_settings.mesh_token)

        if settings.DOCKER_BUILD:
            site = mesh_settings.mesh_site.replace("https", "ws")
            uri = f"{site}:443/control.ashx?auth={token}"
        else:
            site = mesh_settings.mesh_site.replace("https", "wss")
            uri = f"{site}/control.ashx?auth={token}"

        async with websockets.connect(uri) as websocket:

            # Get Invitation Link
            await websocket.send(
                json.dumps(
                    {
                        "action": "createInviteLink",
                        "expire": 8,
                        "flags": 0,
                        "meshname": "TacticalRMM",
                        "responseid": "python",
                    }
                )
            )

            async for message in websocket:
                response = json.loads(message)

                if response["action"] == "createInviteLink":
                    print(response["url"])
                    break

    def handle(self, *args, **kwargs):
        mesh_settings = CoreSettings.objects.first()
        asyncio.get_event_loop().run_until_complete(self.websocket_call(mesh_settings))
