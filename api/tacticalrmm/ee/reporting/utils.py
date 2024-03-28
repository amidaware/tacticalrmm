"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import datetime
import inspect
import json
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union, cast
from zoneinfo import ZoneInfo

import yaml
from django.apps import apps
from jinja2 import Environment, FunctionLoader
from rest_framework.serializers import ValidationError
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from tacticalrmm.utils import get_db_value

from . import custom_filters
from .constants import REPORTING_MODELS
from .markdown.config import Markdown
from .models import ReportAsset, ReportDataQuery, ReportHTMLTemplate, ReportTemplate
from tacticalrmm.utils import RE_DB_VALUE

RE_ASSET_URL = re.compile(
    r"(asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}))"
)

RE_DEPENDENCY_VALUE = re.compile(r"(\{\{\s*(.*)\s*\}\})")


# this will lookup the Jinja parent template in the DB
# Example: {% extends "MASTER_TEMPLATE_NAME or REPORT_TEMPLATE_NAME" %}
def db_template_loader(template_name: str) -> Optional[str]:
    # trys the ReportHTMLTemplate table and ReportTemplate table
    try:
        return ReportHTMLTemplate.objects.get(name=template_name).html
    except ReportHTMLTemplate.DoesNotExist:
        pass

    try:
        template = ReportTemplate.objects.get(name=template_name)
        return template.template_md
    except ReportTemplate.DoesNotExist:
        pass

    return None


# sets up Jinja environment wiht the db loader template
# comment tags needed to be editted because they conflicted with css properties
env = Environment(
    loader=FunctionLoader(db_template_loader),
    comment_start_string="{=",
    comment_end_string="=}",
    extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
)


custom_globals = {
    "datetime": datetime,
    "ZoneInfo": ZoneInfo,
    "re": re,
}

env.globals.update(custom_globals)

# import all functions from custom_filters.py
for name, func in inspect.getmembers(custom_filters, inspect.isfunction):
    env.filters[name] = func


def generate_pdf(*, html: str, css: str = "") -> bytes:
    font_config = FontConfiguration()

    pdf_bytes: bytes = HTML(string=html).write_pdf(
        stylesheets=[CSS(string=css, font_config=font_config)], font_config=font_config
    )

    return pdf_bytes


def generate_html(
    *,
    template: str,
    template_type: str,
    css: str = "",
    html_template: Optional[int] = None,
    variables: str = "",
    dependencies: Optional[Dict[str, int]] = None,
) -> Tuple[str, Dict[str, Any]]:
    if dependencies is None:
        dependencies = {}

    # validate the template
    env.parse(template)

    # convert template
    template_string = (
        Markdown.convert(template) if template_type == "markdown" else template
    )

    # append extends if base template is configured
    if html_template:
        try:
            html_template_name = ReportHTMLTemplate.objects.get(pk=html_template).name
            template_string = (
                f"""{{% extends "{html_template_name}" %}}\n{template_string}"""
            )
        except ReportHTMLTemplate.DoesNotExist:
            pass

    tm = env.from_string(template_string)

    variables_dict = prep_variables_for_template(
        variables=variables, dependencies=dependencies
    )

    return (tm.render(css=css, **variables_dict), variables_dict)


def make_dataqueries_inline(*, variables: str) -> str:
    try:
        variables_obj = yaml.safe_load(variables) or {}
    except (yaml.parser.ParserError, yaml.YAMLError):
        variables_obj = {}

    data_sources = variables_obj.get("data_sources", {})
    if isinstance(data_sources, dict):
        for key, value in data_sources.items():
            if isinstance(value, str):
                try:
                    query = ReportDataQuery.objects.get(name=value).json_query
                    variables_obj["data_sources"][key] = query
                except ReportDataQuery.DoesNotExist:
                    continue

    return yaml.dump(variables_obj)


def prep_variables_for_template(
    *,
    variables: str,
    dependencies: Optional[Dict[str, Any]] = None,
    limit_query_results: Optional[int] = None,
) -> Dict[str, Any]:
    if not dependencies:
        dependencies = {}

    if not variables:
        variables = ""

    # process report dependencies
    variables_dict = process_dependencies(
        variables=variables, dependencies=dependencies
    )

    # replace the data_sources with the actual data from DB. This will be passed to the template
    # in the form of {{data_sources.data_source_name}}
    variables_dict = process_data_sources(
        variables=variables_dict, limit_query_results=limit_query_results
    )

    # generate and replace charts in the variables
    variables_dict = process_chart_variables(variables=variables_dict)

    return variables_dict


class ResolveModelException(Exception):
    pass


def resolve_model(*, data_source: Dict[str, Any]) -> Dict[str, Any]:
    tmp_data_source = data_source

    # check that model property is present and correct
    if "model" in data_source:
        for model, app in REPORTING_MODELS:
            if data_source["model"].lower() == model.lower():
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


class AllowedOperations(Enum):
    # filtering
    ONLY = "only"
    DEFER = "defer"
    FILTER = "filter"
    EXCLUDE = "exclude"
    LIMIT = "limit"
    GET = "get"
    FIRST = "first"
    ALL = "all"
    # custom fields
    CUSTOM_FIELDS = "custom_fields"
    # presentation
    JSON = "json"
    CSV = "csv"
    # relations
    SELECT_RELATED = "select_related"
    PREFETCH_RELATED = "prefetch_related"
    # operations
    AGGREGATE = "aggregate"
    ANNOTATE = "annotate"
    COUNT = "count"
    VALUES = "values"
    # ordering
    ORDER_BY = "order_by"


class InvalidDBOperationException(Exception):
    pass


def build_queryset(*, data_source: Dict[str, Any], limit: Optional[int] = None) -> Any:
    local_data_source = data_source
    Model = local_data_source.pop("model")
    count = False
    get = False
    first = False
    all = False
    isJson = False
    isCsv = False
    csv_columns = {}
    defer = local_data_source.get("defer", None)
    columns = local_data_source.get("only", None)
    fields_to_add = []

    # create a base reporting queryset
    queryset = Model.objects.using("default")
    model_name = Model.__name__.lower()
    for operation, values in local_data_source.items():
        # Usage in the build_queryset function:
        if operation not in [op.value for op in AllowedOperations]:
            raise InvalidDBOperationException(
                f"DB operation: {operation} not allowed. Supported operations: {', '.join(op.value for op in AllowedOperations)}"
            )

        if operation == "meta":
            continue
        elif operation == "custom_fields" and isinstance(values, list):
            from core.models import CustomField

            if model_name in ("client", "site", "agent"):
                fields = CustomField.objects.filter(model=model_name)
                fields_to_add = [
                    field for field in values if fields.filter(name=field).exists()
                ]

        elif operation == "limit":
            limit = values
        elif operation == "count":
            count = True
        elif operation == "get":
            # need to add a filter for the get if present
            if isinstance(values, dict):
                queryset = queryset.filter(**values)
            get = True
        elif operation == "first":
            first = True
        elif operation == "all":
            all = True
        elif operation == "json":
            isJson = True
        elif operation == "csv":
            if isinstance(values, dict):
                csv_columns = values
            isCsv = True
        elif isinstance(values, list):
            queryset = getattr(queryset, operation)(*values)
        elif isinstance(values, dict):
            queryset = getattr(queryset, operation)(**values)
        else:
            queryset = getattr(queryset, operation)(values)

    if all:
        queryset = queryset.all()

    if count:
        return queryset.count()

    if limit and not first and not get:
        queryset = queryset[:limit]

    if columns:
        # remove columns from only if defer is also present
        if defer:
            columns = [column for column in columns if column not in defer]
        if "id" not in columns:
            columns.append("id")

        queryset = queryset.values(*columns)
    elif defer:
        # Since values seems to ignore only and defer, we need to get all columns and remove the defered ones.
        # Then we can pass the rest of the columns in
        included_fields = [
            field.name for field in Model._meta.local_fields if field.name not in defer
        ]
        queryset = queryset.values(*included_fields)
    else:
        queryset = queryset.values()

    if get or first:
        if get:
            queryset = queryset.get()
        elif first:
            queryset = queryset.first()

        if fields_to_add:
            queryset = add_custom_fields(
                data=queryset,
                fields_to_add=fields_to_add,
                model_name=model_name,
                dict_value=True,
            )

        if isJson:
            return json.dumps(queryset, default=str)
        elif isCsv:
            import pandas as pd

            df = pd.DataFrame.from_dict([queryset])
            df.drop("id", axis=1, inplace=True)
            if csv_columns:
                df = df.rename(columns=csv_columns)
            return df.to_csv(index=False)
        else:
            return queryset
    else:
        # add custom fields for list results
        queryset = list(queryset)

        if fields_to_add:
            queryset = add_custom_fields(
                data=queryset, fields_to_add=fields_to_add, model_name=model_name
            )

        if isJson:
            return json.dumps(queryset, default=str)
        elif isCsv:
            import pandas as pd

            df = pd.DataFrame.from_dict(queryset)
            df.drop("id", axis=1, inplace=True)
            if csv_columns:
                df = df.rename(columns=csv_columns)
            return df.to_csv(index=False)
        else:
            return queryset


def add_custom_fields(
    *,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    fields_to_add: List[str],
    model_name: Literal["client", "site", "agent"],
    dict_value: bool = False,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    from agents.models import AgentCustomField
    from clients.models import ClientCustomField, SiteCustomField
    from core.models import CustomField

    model_name = model_name.lower()
    CustomFieldModel: Union[
        Type[AgentCustomField], Type[ClientCustomField], Type[SiteCustomField]
    ]
    if model_name == "agent":
        CustomFieldModel = AgentCustomField
    elif model_name == "client":
        CustomFieldModel = ClientCustomField
    else:
        CustomFieldModel = SiteCustomField

    custom_fields = CustomField.objects.filter(name__in=fields_to_add, model=model_name)

    if dict_value:
        custom_field_data = list(
            CustomFieldModel.objects.select_related("field").filter(
                field__name__in=fields_to_add, **{f"{model_name}_id": data["id"]}
            )
        )
        # hold custom field data on the returned object
        data["custom_fields"]: Dict[str, Any] = {}

        for custom_field in custom_fields:
            find_custom_field_data = next(
                (cf for cf in custom_field_data if cf.field_id == custom_field.id),
                None,
            )

            if find_custom_field_data is not None:
                data["custom_fields"][custom_field.name] = find_custom_field_data.value
            else:
                data["custom_fields"][custom_field.name] = custom_field.default_value

        return data
    else:
        ids = [row["id"] for row in data]
        custom_field_data = list(
            CustomFieldModel.objects.select_related("field").filter(
                field__name__in=fields_to_add, **{f"{model_name}_id__in": ids}
            )
        )

        for row in data:
            row["custom_fields"]: Dict[str, Any] = {}

            for custom_field in custom_fields:
                find_custom_field_data = next(
                    (
                        cf
                        for cf in custom_field_data
                        if cf.field_id == custom_field.id
                        and getattr(cf, f"{model_name}_id") == row["id"]
                    ),
                    None,
                )

                if find_custom_field_data is not None:
                    row["custom_fields"][
                        custom_field.name
                    ] = find_custom_field_data.value
                else:
                    row["custom_fields"][custom_field.name] = custom_field.default_value

        return data


def normalize_asset_url(text: str, type: Literal["pdf", "html", "plaintext"]) -> str:
    new_text = text
    for url, id in RE_ASSET_URL.findall(text):
        try:
            asset = ReportAsset.objects.get(id=id)
            if type == "html":
                new_text = new_text.replace(
                    f"asset://{id}", f"{asset.file.url}?id={id}"
                )
            else:
                new_text = new_text.replace(f"{url}", f"file://{asset.file.path}")
        except ReportAsset.DoesNotExist:
            pass

    return new_text


def base64_encode_assets(template: str) -> List[Dict[str, Any]]:
    import base64

    assets = []
    added_ids = []
    for _, id in RE_ASSET_URL.findall(template):
        if id not in added_ids:
            try:
                asset = ReportAsset.objects.get(pk=id)

                encoded_base64_str = base64.b64encode(asset.file.file.read()).decode(
                    "utf-8"
                )
                assets.append(
                    {
                        "id": asset.id,
                        "name": asset.file.name,
                        "file": encoded_base64_str,
                    }
                )
                added_ids.append(
                    str(asset.id)
                )  # need to convert uuid to str for easy comparison
            except ReportAsset.DoesNotExist:
                continue

    return assets


def decode_base64_asset(asset: str) -> bytes:
    import base64

    return base64.b64decode(asset.encode("utf-8"))


def process_data_sources(
    *, variables: Dict[str, Any], limit_query_results: Optional[int] = None
) -> Dict[str, Any]:
    data_sources = variables.get("data_sources")

    if isinstance(data_sources, dict):
        for key, value in data_sources.items():
            if isinstance(value, dict):
                modified_datasource = resolve_model(data_source=value)
                queryset = build_queryset(
                    data_source=modified_datasource, limit=limit_query_results
                )
                data_sources[key] = queryset

    return variables


def process_dependencies(
    *, variables: str, dependencies: Dict[str, Any]
) -> Dict[str, Any]:
    DEPENDENCY_MODELS = {
        "client": ("clients", "Client"),
        "site": ("clients", "Site"),
        "agent": ("agents", "Agent"),
    }

    # Resolve dependencies that are agent, site, or client
    for dep, (app_label, model_name) in DEPENDENCY_MODELS.items():
        if dep in dependencies:
            Model = apps.get_model(app_label, model_name)
            # Assumes each model has a unique lookup mechanism
            lookup_param = "agent_id" if dep == "agent" else "id"
            dependencies[dep] = Model.objects.get(**{lookup_param: dependencies[dep]})

    # Handle database value placeholders
    for string, model, prop in RE_DB_VALUE.findall(variables):
        value = get_value_for_model(model, prop, dependencies)
        if value:
            variables = variables.replace(string, str(value))

    # Handle non-database dependencies
    for string, dep in RE_DEPENDENCY_VALUE.findall(variables):
        value = dependencies.get(dep)
        if value:
            variables = variables.replace(string, str(value))

    # Load yaml variables if they exist
    variables = yaml.safe_load(variables) or {}

    return {**variables, **dependencies}


def get_value_for_model(model: str, prop: str, dependencies: Dict[str, Any]) -> Any:
    if model == "global":
        return get_db_value(string=f"{model}.{prop}")
    instance = dependencies.get(model)
    return get_db_value(string=prop, instance=instance) if instance else None


def process_chart_variables(*, variables: Dict[str, Any]) -> Dict[str, Any]:
    charts = variables.get("charts")

    if not isinstance(charts, dict):
        return variables

    # these will be remove so they don't render in the template
    invalid_chart_keys = []

    for key, chart in charts.items():
        options = chart.get("options")
        if not isinstance(options, dict):
            continue

        data_frame = options.get("data_frame")
        if isinstance(data_frame, str):
            data_source = data_frame.split(".")
            data = variables

            path_exists = True
            for path in data_source:
                data = data.get(path)
                if data is None:
                    path_exists = False
                    break

            if not path_exists:
                continue

            if not data:
                invalid_chart_keys.append(key)
                continue

            options["data_frame"] = data

        traces = chart.get("traces")
        layout = chart.get("layout")
        charts[key] = generate_chart(
            type=chart["chartType"],
            format=chart["outputType"],
            options=options,
            traces=traces,
            layout=layout,
        )

    for key in invalid_chart_keys:
        del charts[key]

    return variables


def generate_chart(
    *,
    type: Literal["pie", "bar", "line"],
    format: Literal["html", "image"],
    options: Dict[str, Any],
    traces: Optional[Dict[str, Any]] = None,
    layout: Optional[Dict[str, Any]] = None,
) -> str:
    # TODO figure out why plotly affects perf
    import plotly.express as px

    fig = getattr(px, type)(**options)

    if traces:
        fig.update_traces(**traces)

    if layout:
        fig.update_layout(**layout)

    if format == "html":
        return cast(str, fig.to_html(full_html=False, include_plotlyjs="cdn"))
    elif format == "image":
        return cast(str, fig.to_image(format="svg").decode("utf-8"))


# import report functions
def _import_base_template(
    base_template_data: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
) -> Optional[int]:
    if base_template_data:
        # Check name conflict and modify name if necessary
        name = base_template_data.get("name")
        html = base_template_data.get("html")

        if not name:
            raise ValidationError("base_template is missing 'name' key")
        if not html:
            raise ValidationError("base_template is missing 'html' field")

        if ReportHTMLTemplate.objects.filter(name=name).exists():
            base_template = ReportHTMLTemplate.objects.filter(name=name).get()
            if overwrite:
                base_template.html = html
                base_template.save()
            else:
                name += f"_{_generate_random_string()}"
                base_template = ReportHTMLTemplate.objects.create(name=name, html=html)
        else:
            base_template = ReportHTMLTemplate.objects.create(name=name, html=html)

        base_template.refresh_from_db()
        return base_template.id
    return None


def _import_report_template(
    report_template_data: Dict[str, Any],
    base_template_id: Optional[int] = None,
    overwrite: bool = False,
) -> "ReportTemplate":
    if report_template_data:
        name = report_template_data.pop("name", None)
        template_md = report_template_data.get("template_md")

        if not name:
            raise ValidationError("template requires a 'name' key")
        if not template_md:
            raise ValidationError("template requires a 'template_md' field")

        if ReportTemplate.objects.filter(name=name).exists():
            report_template = ReportTemplate.objects.filter(name=name).get()
            if overwrite:
                for key, value in report_template_data.items():
                    setattr(report_template, key, value)

                report_template.save()
            else:
                name += f"_{_generate_random_string()}"
                report_template = ReportTemplate.objects.create(
                    name=name,
                    template_html_id=base_template_id,
                    **report_template_data,
                )
        else:
            report_template = ReportTemplate.objects.create(
                name=name, template_html_id=base_template_id, **report_template_data
            )
        report_template.refresh_from_db()
        return report_template
    else:
        raise ValidationError("'template' key is required in input")


def _import_assets(assets: List[Dict[str, Any]]) -> None:
    import io
    import os

    from django.core.files import File

    from .storage import report_assets_fs

    if isinstance(assets, list):
        for asset in assets:
            parent_folder = report_assets_fs.getreldir(path=asset["name"])
            path = report_assets_fs.get_available_name(
                os.path.join(parent_folder, asset["name"])
            )
            asset_obj = ReportAsset(
                id=asset["id"],
                file=File(
                    io.BytesIO(decode_base64_asset(asset["file"])),
                    name=path,
                ),
            )
            asset_obj.save()


def _generate_random_string(length: int = 6) -> str:
    import random
    import string

    return "".join(random.choice(string.ascii_lowercase) for i in range(length))
