import os

from django.core.files.storage import FileSystemStorage

from .settings import settings

class SysTrayAssetStorage(FileSystemStorage):

        def isfile(self, *, path: str) -> bool:
                return os.path.isfile(self.path(name=path))

        def isico(self, *, path: str) -> bool:
                filepath = self.path(name=path)
                return os.path.isfile(filepath) and filepath.lower().endswith('.ico')

systray_assets_fs = SysTrayAssetStorage(
    location=settings.SYSTRAY_ASSETS_BASE_PATH,
    base_url=f"{settings.SYSTRAY_BASE_URL}/core/systray/",
)


def get_systray_assets_fs():
    return systray_assets_fs