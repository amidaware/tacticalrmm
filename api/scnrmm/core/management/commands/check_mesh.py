import asyncio

from django.core.management.base import BaseCommand
from meshctrl.utils import get_auth_token

from core.utils import get_core_settings, get_mesh_device_id, get_mesh_ws_url


class Command(BaseCommand):
    help = "Mesh troubleshooting script"

    def _success(self, *args) -> None:
        self.stdout.write(self.style.SUCCESS(" ".join(args)))

    def _error(self, *args) -> None:
        self.stdout.write(self.style.ERROR(" ".join(args)))

    def _warning(self, *args) -> None:
        self.stdout.write(self.style.WARNING(" ".join(args)))

    def handle(self, *args, **kwargs) -> None:
        core = get_core_settings()

        self._warning("Mesh site:", core.mesh_site)
        self._warning("Mesh username:", core.mesh_username)
        self._warning("Mesh token:", core.mesh_token)
        self._warning("Mesh device group:", core.mesh_device_group)

        try:
            token = get_auth_token(core.mesh_api_superuser, core.mesh_token)
        except Exception as e:
            self._error("Error getting auth token:")
            self._error(str(e))
            return
        else:
            self._success("Auth token ok:")
            self._success(token)

        try:
            uri = get_mesh_ws_url()
        except Exception as e:
            self._error("Error getting mesh url:")
            self._error(str(e))
            return
        else:
            self._success("Mesh url ok:")
            self._success(uri)

        try:
            mesh_id = asyncio.run(get_mesh_device_id(uri, core.mesh_device_group))
        except IndexError:
            self._error(
                "Error: you are using a custom mesh device group name. The name in TRMMs Global Settings > MeshCentral must match a MeshCentral group exactly."
            )
            return
        except Exception as e:
            self._error("Error getting mesh device id:")
            self._error(str(e))
            return
        else:
            self._success("Mesh device id ok:", mesh_id)
