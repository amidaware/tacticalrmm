"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from typing import Optional, Sequence, Union

import markdown

from .ignorejinja_ext import IgnoreJinjaExtension

markdown_ext: "Optional[Sequence[Union[str, markdown.Extension]]]" = [
    "ocxsect",
    "tables",
    "sane_lists",
    "def_list",
    "nl2br",
    "fenced_code",
    "attr_list",
    IgnoreJinjaExtension(),
]

# import this into views
Markdown = markdown.Markdown(extensions=markdown_ext)
