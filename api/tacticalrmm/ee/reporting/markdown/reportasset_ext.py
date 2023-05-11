"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from typing import List, Any, TYPE_CHECKING
from markdown import Extension, Markdown
from markdown.preprocessors import Preprocessor

from django.apps import apps


if TYPE_CHECKING:
    from ..models import ReportAsset as ReportAssetType

# looking for asset://123e4567-e89b-12d3-a456-426614174000 and replaces with actual path to render image
RE = re.compile(
    r"asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12})"
)


class ReportAssetExtension(Extension):
    """Extension for looking up asset://{uuid4} urls in the DB"""

    def extendMarkdown(self, md: Markdown) -> None:
        """Add ReportAssetExtension to Markdown instance."""
        md.preprocessors.register(ReportAssetPreprocessor(md), "reportasset", 0)


class ReportAssetPreprocessor(Preprocessor):
    """
    Looks for asset://123e4567-e89b-12d3-a456-426614174000 and replaces with actual
    path on the file system to render image
    """

    def run(self, lines: List[str]) -> List[str]:
        new_lines: List[str] = []
        for line in lines:
            m = RE.search(line)
            if m:
                asset_id = m.group(1)
                ReportAsset = apps.get_model("reporting", "ReportAsset")

                asset: "ReportAssetType" = ReportAsset.objects.get(id=asset_id)

                new_line = line.replace(f"asset://{asset_id}", f"{asset.file.url}?id={asset_id}")

                new_lines.append(new_line)
            else:
                new_lines.append(line)

        return new_lines


def makeExtension(*args: Any, **kwargs: Any) -> ReportAssetExtension:
    """set up extension."""
    return ReportAssetExtension(*args, **kwargs)
