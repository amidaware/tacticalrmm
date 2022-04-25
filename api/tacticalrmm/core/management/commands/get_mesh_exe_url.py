import asyncio
import json

import websockets
from django.core.management.base import BaseCommand

from core.utils import get_mesh_ws_url


class Command(BaseCommand):
    help = "Sets up initial mesh central configuration"

    async def websocket_call(self, uri):

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
                    self.stdout.write(response["url"].replace(":4443", ":443"))
                    break

    def handle(self, *args, **kwargs):
        uri = get_mesh_ws_url()
        asyncio.run(self.websocket_call(uri))
