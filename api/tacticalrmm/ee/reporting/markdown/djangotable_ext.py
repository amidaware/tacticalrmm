"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from typing import List, Any
from markdown import Extension, Markdown
from markdown.preprocessors import Preprocessor

from django.apps import apps
from ..utils import resolve_model, build_queryset
import pandas as pd


RE = re.compile(r"\\table\((.*)\)")


class DjangoTableExtension(Extension):
    """Extension for parsing Django querysets into markdown tables"""

    def extendMarkdown(self, md: Markdown) -> None:
        """Add DjangoTableExtension to Markdown instance."""
        md.preprocessors.register(DjangoTablePreprocessor(md), "djangotable", 0)


class DjangoTablePreprocessor(Preprocessor):
    """
    Looks for \\table(datasource) and executes the query and uses pandas to convert to markdown table.
    Uses a special reporting connection to limit access to SELECTS and only certain tables.
    """

    def run(self, lines: List[str]) -> List[str]:
        inline_data_sources = (
            self.md.Meta["data_sources"]
            if hasattr(self.md, "Meta")
            and self.md.Meta
            and "data_sources" in self.md.Meta.keys()
            else None
        )

        new_lines: List[str] = []
        for line in lines:
            m = RE.search(line)
            if m:
                data_query_name = m.group(1)
                if (
                    inline_data_sources
                    and data_query_name in inline_data_sources.keys()
                ):
                    data_source = inline_data_sources[m.group(1)]
                else:
                    # no inline data sources found in yaml, check if it exists in DB
                    ReportDataQuery = apps.get_model("reporting", "ReportDataQuery")
                    try:
                        data_source = ReportDataQuery.objects.get(
                            name=data_query_name
                        ).json_query
                    except ReportDataQuery.DoesNotExist:
                        new_lines.append(line)
                        continue

                meta = data_source.pop("meta") if "meta" in data_source.keys() else None

                modified_datasource = resolve_model(data_source=data_source)
                queryset = build_queryset(data_source=modified_datasource)
                df = pd.DataFrame.from_records(queryset)

                if meta:
                    if "rename_columns" in meta.keys():
                        df.rename(columns=meta["rename_columns"], inplace=True)

                new_lines = new_lines + df.to_markdown(index=False).split("\n")
            else:
                new_lines.append(line)

        return new_lines


def makeExtension(*args: Any, **kwargs: Any) -> DjangoTableExtension:
    """set up extension."""
    return DjangoTableExtension(*args, *kwargs)
