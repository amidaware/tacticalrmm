from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import CoreSettings
from .helpers import get_auth_token
import asyncio
import websockets
import json


class Command(BaseCommand):
    help = "Sets up initial mesh central configuration"

    async def websocket_call(self):

        token = get_auth_token(
            self.mesh_settings.mesh_username, self.mesh_settings.mesh_token
        )

        if settings.MESH_WS_URL:
            uri = f"{settings.MESH_WS_URL}/control.ashx?auth={token}"
        else:
            site = self.mesh_settings.mesh_site.replace("https", "wss")
            uri = f"{site}/control.ashx?auth={token}"

        async with websockets.connect(uri) as websocket:

            # Get Device groups to see if it exists
            await websocket.send(json.dumps({"action": "meshes"}))

            async for message in websocket:
                response = json.loads(message)
                if response["action"] == "meshes":

                    # If no meshes are present
                    if not response["meshes"]:
                        await websocket.send(
                            json.dumps(
                                {
                                    "action": "createmesh",
                                    "meshname": "TacticalRMM",
                                    "meshtype": 2,
                                    "responseid": "python",
                                }
                            )
                        )
                        break
                    else:
                        break

    def handle(self, *args, **kwargs):
        self.mesh_settings = CoreSettings.objects.first()
        asyncio.get_event_loop().run_until_complete(self.websocket_call())
        self.stdout.write("Initial Mesh Central setup complete")
