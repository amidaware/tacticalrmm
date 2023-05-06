"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from typing import Dict, List, Any
from markdown import Extension, Markdown
from markdown.preprocessors import Preprocessor

from django.apps import apps
from ..constants import REPORTING_MODELS

import pandas as pd


class ResolveModelException(Exception):
    pass


def resolve_model(*, data_source: Dict[str, Any]) -> Dict[str, Any]:
    tmp_data_source = data_source

    # check that model property is present and correct
    if "model" in data_source.keys():
        for model, app in REPORTING_MODELS:
            if data_source["model"].capitalize() == model:
                try:
                    # overwrite model with the model type
                    tmp_data_source["model"] = apps.get_model(app, model)
                    return tmp_data_source
                except LookupError:
                    raise ResolveModelException(
                        f"Model: {model} does not exist in app: {app}"
                    )
        raise ResolveModelException(f"Model lookup failed for {data_source['model']}")
    else:
        raise ResolveModelException("Model key must be present on data_source")


ALLOWED_OPERATIONS = (
    # filtering
    "only",
    "defer",
    "filter",
    "exclude",
    "limit",
    # relations
    "select_related",
    "prefetch_related",
    # operations
    "aggregate",
    "annotate",
    # ordering
    "order_by",
)


class InvalidDBOperationException(Exception):
    pass


def build_queryset(*, data_source: Dict[str, Any]) -> Any:
    local_data_source = data_source
    Model = local_data_source.pop("model")
    limit = None
    columns = local_data_source["only"] if "only" in local_data_source.keys() else None

    # create a base reporting queryset
    queryset = Model.objects.using("reporting")

    for operation, values in local_data_source.items():
        if operation not in ALLOWED_OPERATIONS:
            raise InvalidDBOperationException(
                f"DB operation: {operation} not allowed. Supported operations: only, defer, filter, exclude, limit, select_related, prefetch_related, annotate, aggregate, order_by"
            )

        if operation == "meta":
            continue
        elif operation == "limit":
            limit = values
        elif isinstance(values, list):
            queryset = getattr(queryset, operation)(*values)
        elif isinstance(values, dict):
            queryset = getattr(queryset, operation)(**values)
        else:
            queryset = getattr(queryset, operation)(values)

    if limit:
        queryset = queryset[:limit]

    if columns:
        queryset = queryset.values(*columns)
    else:
        queryset = queryset.values()

    return queryset


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
