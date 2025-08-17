"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import os
import shutil

from django.core.files.storage import FileSystemStorage

from .settings import settings


class ReportAssetStorage(FileSystemStorage):
    """Report Asset file storage object. This keeps file system
    operations confined to REPORT_ASSETS_PATH
    """

    def isdir(self, *, path: str) -> bool:
        """Checks if path is a directory"""
        return os.path.isdir(self.path(name=path))

    def isfile(self, *, path: str) -> bool:
        """Checks if path is a file"""
        return os.path.isfile(self.path(name=path))

    def getfulldir(self, *, path: str) -> str:
        """Returns the absolute path of the parent folder"""
        return os.path.dirname(self.path(name=path))

    def getreldir(self, *, path: str) -> str:
        """Returns relative path of the parent folder. The path is relative to
        REPORT_ASSETS_PATH.
        """
        if self.exists(path):
            return os.path.dirname(path)

        return ""

    def rename(self, *, path: str, new_name: str) -> str:
        """Renames the file or folder specified. If the name is already taken
        then 6 random characters (_cb6dge) will be appended to the name
        """
        parent_folder = self.getreldir(path=path)
        new_path = self.get_available_name(os.path.join(parent_folder, new_name))
        os.rename(self.path(path), self.path(new_path))
        return new_path

    def createfolder(self, *, path: str) -> str:
        """Create a folder in the specified path"""
        new_path = self.get_available_name(path)
        os.mkdir(os.path.join(self.base_location, new_path))
        return new_path

    def move(self, *, source: str, destination: str) -> str:
        """Move a file or directory to the destination. If the file or folder
        name conflicts, the new name will have additional characters appended.
        """
        new_destination = self.get_available_name(
            os.path.join(destination, source.split("/")[-1])
        )

        shutil.move(self.path(source), self.path(new_destination))
        return new_destination


report_assets_fs = ReportAssetStorage(
    location=settings.REPORTING_ASSETS_BASE_PATH,
    base_url=f"{settings.REPORTING_BASE_URL}/reporting/assets/",
)


def get_report_assets_fs():
    return report_assets_fs
