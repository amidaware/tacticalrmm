"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from typing import Any, List

from markdown import Extension, Markdown
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor


class IgnoreJinjaExtension(Extension):
    """Extension for looking up {% block tag %}"""

    def extendMarkdown(self, md: Markdown) -> None:
        """Add IgnoreJinjaExtension to Markdown instance."""
        md.preprocessors.register(IgnoreJinjaPreprocessor(md), "preignorejinja", 0)
        md.postprocessors.register(IgnoreJinjaPostprocessor(md), "postignorejinja", 0)


PRE_RE = re.compile(r"(\{\%.*\%\})")


class IgnoreJinjaPreprocessor(Preprocessor):
    """
    Looks for {% block tag %} and wraps it in an html comment <!---  -->
    """

    def run(self, lines: List[str]) -> List[str]:
        new_lines: List[str] = []
        for line in lines:
            m = PRE_RE.search(line)
            if m:
                tag = m.group(1)
                new_line = line.replace(tag, f"<!--- {tag} -->")
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        return new_lines


POST_RE = re.compile(r"\<\!\-\-\-\s{1}(\{\%.*\%\})\s{1}\-\-\>")


class IgnoreJinjaPostprocessor(Postprocessor):
    """
    Looks for <!-- {{% block tag %}} --> and removes the comment
    """

    def run(self, text: str) -> str:
        new_lines: List[str] = []
        lines = text.split("\n")
        for line in lines:
            m = POST_RE.search(line)
            if m:
                tag = m.group(1)
                new_line = line.replace(f"<!--- {tag} -->", tag)
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        return "\n".join(new_lines)


def makeExtension(*args: Any, **kwargs: Any) -> IgnoreJinjaExtension:
    """set up extension."""
    return IgnoreJinjaExtension(*args, **kwargs)
