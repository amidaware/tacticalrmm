"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from typing import Optional, Sequence, Union
import markdown
import yaml

# from .djangotable_ext import DjangoTableExtension
from .reportasset_ext import ReportAssetExtension
from .ignorejinja_ext import IgnoreJinjaExtension

markdown_ext: "Optional[Sequence[Union[str, markdown.Extension]]]" = [
    "ocxsect",
    "tables",
    "sane_lists",
    "def_list",
    "nl2br",
    "fenced_code",
    "full_yaml_metadata",
    "attr_list",
    ReportAssetExtension(),
    IgnoreJinjaExtension(),
    # DjangoTableExtension(),
]

extension_config = {
    "full_yaml_metadata": {
        "yaml_loader": yaml.SafeLoader,
    },
}

# import this into views
Markdown = markdown.Markdown(
    extensions=markdown_ext, extension_configs=extension_config
)
