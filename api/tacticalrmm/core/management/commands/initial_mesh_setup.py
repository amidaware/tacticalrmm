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
        mesh_settings = CoreSettings.objects.first()

        try:
            # Check for Mesh Username
            if (
                not mesh_settings.mesh_username
                or settings.MESH_USERNAME != mesh_settings.mesh_username
            ):
                mesh_settings.mesh_username = settings.MESH_USERNAME

            # Check for Mesh Site
            if (
                not mesh_settings.mesh_site
                or settings.MESH_SITE != mesh_settings.mesh_site
            ):
                mesh_settings.mesh_site = settings.MESH_SITE

            # Check for Mesh Token
            if (
                not mesh_settings.mesh_token
                or settings.MESH_TOKEN_KEY != mesh_settings.mesh_token
            ):
                mesh_settings.mesh_token = settings.MESH_TOKEN_KEY

            mesh_settings.save()

        except AttributeError:
            self.stdout.write(
                "Mesh Setup was skipped because the configuration wasn't available. Needs to be setup manually."
            )
            return

        try:
            asyncio.get_event_loop().run_until_complete(
                self.websocket_call(mesh_settings)
            )
            self.stdout.write("Initial Mesh Central setup complete")
        except websockets.exceptions.ConnectionClosedError:
            self.stdout.write(
                "Unable to connect to MeshCentral. Please verify it is online and the configuration is correct in the settings."
            )
