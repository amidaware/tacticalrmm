"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from pathlib import Path

import pytest
from django.core.exceptions import SuspiciousFileOperation

from ..storage import ReportAssetStorage


def test_is_file(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"
    file = tmp_path / "file"

    dir.mkdir()
    file.touch()
    assert not storage.isfile(path="temp")
    assert storage.isfile(path="file")


def test_is_file_wrong_path(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    assert not storage.isfile(path="doesntexist")


def test_is_dir(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"
    file = tmp_path / "file"

    dir.mkdir()
    file.touch()
    assert storage.isdir(path="temp")
    assert not storage.isdir(path="file")


def test_is_dir_wrong_path(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    assert not storage.isdir(path="doesntexist")


def test_get_full_dir(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"
    file = tmp_path / "temp/file"

    dir.mkdir()
    file.touch()

    assert storage.getfulldir(path="temp") == str(tmp_path)
    assert storage.getfulldir(path="temp/file") == str(tmp_path / "temp")


def test_full_dir_directory_traversal(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    with pytest.raises(SuspiciousFileOperation):
        # test with relative path
        storage.getfulldir(path="../..")

    with pytest.raises(SuspiciousFileOperation):
        # test with absolute path
        storage.getfulldir(path="/etc")


def test_get_rel_dir(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"  # {tmp_path}/temp -> ''
    file = tmp_path / "temp/file"  # {tmp_path}/temp/file -> 'temp'
    nested_dir = dir / "nested"  # {tmp_path}/temp/nested -> 'temp'
    nested_dir2 = (
        nested_dir / "nested"
    )  # {tmp_path}/temp/nested/nested -> 'temp/nested'

    dir.mkdir()
    file.touch()
    nested_dir.mkdir()
    nested_dir2.mkdir()

    assert storage.getreldir(path="temp") == ""
    assert storage.getreldir(path="temp/file") == "temp"
    assert storage.getreldir(path="temp/nested") == "temp"
    assert storage.getreldir(path="temp/nested/nested") == "temp/nested"


def test_rename_file(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    file = tmp_path / "file"

    file.touch()

    new_path = storage.rename(path="file", new_name="newfilename")

    assert new_path == "newfilename"


def test_rename_directory(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"
    dir2 = tmp_path / "temp2"
    dir3 = dir2 / "nested"

    dir.mkdir()
    dir2.mkdir()
    dir3.mkdir()

    new_path = storage.rename(path="temp", new_name="newfoldername")
    new_path_nested = storage.rename(path="temp2/nested", new_name="newfoldername")

    assert new_path == "newfoldername"
    assert new_path_nested == "temp2/newfoldername"


def test_rename_with_conflicting_path(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"
    dir2 = tmp_path / "temp2"

    dir.mkdir()
    dir2.mkdir()

    new_path = storage.rename(path="temp2", new_name="temp")

    assert new_path != "temp"
    assert new_path.startswith("temp_")


def test_rename_with_invalid_path(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    with pytest.raises(FileNotFoundError):
        storage.rename(path="path", new_name="doesntexist")


def test_rename_denies_directory_traversal(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    with pytest.raises(SuspiciousFileOperation):
        # relative
        storage.rename(path="../../etc", new_name="doesntexist")

    with pytest.raises(SuspiciousFileOperation):
        # absolute
        storage.rename(path="/etc", new_name="doesntexist")


def test_create_folder(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)
    dir = tmp_path / "temp"
    dir_nested = dir / "nested"

    dir.mkdir()
    dir_nested.mkdir()

    new_path = storage.createfolder(path="temp/newfoldername")
    new_path_nested = storage.createfolder(path="temp/nested/newfoldername")

    assert new_path == "temp/newfoldername"
    assert new_path_nested == "temp/nested/newfoldername"


def test_create_folder_with_conflicting_name(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"

    dir.mkdir()

    new_path = storage.createfolder(path="temp")

    assert new_path != "temp"
    assert new_path.startswith("temp_")


def test_create_folder_directory_traversal(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    with pytest.raises(SuspiciousFileOperation):
        # relative
        storage.createfolder(path="../../etc")

    with pytest.raises(SuspiciousFileOperation):
        # absolute
        storage.createfolder(path="/etc")


def test_move_folder(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"
    file = dir / "file"

    dir.mkdir()
    file.touch()

    new_path = storage.move(source="temp", destination="dest")

    assert new_path == "dest/temp"
    assert storage.exists("dest/temp/file")


def test_move_file(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"
    file = dir / "file"
    dest = tmp_path / "dest"

    dir.mkdir()
    file.touch()
    dest.mkdir()

    new_path = storage.move(source="temp/file", destination="dest")

    assert new_path == "dest/file"


def test_move_file_with_file_conflict(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"
    file = dir / "file"

    dest_dir = tmp_path / "dest"
    dest_file = dest_dir / "file"

    dir.mkdir()
    file.touch()
    dest_dir.mkdir()
    dest_file.mkdir()

    new_path = storage.move(source="temp/file", destination="dest")

    assert new_path != "dest/file"
    assert new_path.startswith("dest/file_")


def test_move_folder_with_name_conflict(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    dir = tmp_path / "temp"
    file = dir / "file"

    dir.mkdir()
    file.touch()

    new_path = storage.move(source="temp", destination="")

    assert new_path != "temp"
    assert new_path.startswith("temp_")


def test_move_directory_traversal(tmp_path: Path) -> None:
    storage = ReportAssetStorage(location=tmp_path)

    with pytest.raises(SuspiciousFileOperation):
        # relative
        storage.move(source="../../file", destination="../..")

    with pytest.raises(SuspiciousFileOperation):
        # absolute
        storage.move(source="/etc", destination="/newpath")
