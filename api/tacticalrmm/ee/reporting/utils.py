"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
import json
from typing import Any, Dict, List, Tuple, Literal, Optional, Union, Type, cast

import plotly.express as px
import yaml
from django.apps import apps
from jinja2 import Environment, FunctionLoader
from tacticalrmm.utils import get_db_value
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from .constants import REPORTING_MODELS
from .markdown.config import Markdown
from .models import ReportAsset, ReportHTMLTemplate, ReportTemplate


# regex for db data replacement
# will return 3 groups of matches in a tuple when uses with re.findall
# i.e. - {{client.name}}, client.name, client
RE_DB_VALUE = re.compile(r"(\{\{\s*(client|site|agent|global)\.(.*)\s*\}\})")

RE_ASSET_URL = re.compile(
    r"(asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}))"
)


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
    except ReportHTMLTemplate.DoesNotExist:
        pass

    return None


# sets up Jinja environment wiht the db loader template
# comment tags needed to be editted because they conflicted with css properties
env = Environment(
    loader=FunctionLoader(db_template_loader),
    comment_start_string="{=",
    comment_end_string="=}",
)


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
    dependencies: Dict[str, int] = {},
) -> Tuple[str, Optional[Dict[str, Any]]]:
    # validate the template before doing anything. This will throw a TemplateError exception
    env.parse(template)

    # convert template from markdown to html if type is markdown
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

    variables = prep_variables_for_template(
        variables=variables, dependencies=dependencies
    )
    if variables:
        return (tm.render(css=css, **variables), variables)
    else:
        return (tm.render(css=css), None)


def make_dataqueries_inline(*, variables: str) -> str:
    variables_obj = yaml.safe_load(variables) or {}
    if "data_sources" in variables_obj.keys() and isinstance(
        variables_obj["data_sources"], dict
    ):
        for key, value in variables_obj["data_sources"].items():
            # data_source is referencing a saved data query
            if isinstance(value, str):
                ReportDataQuery = apps.get_model("reporting", "ReportDataQuery")
                try:
                    variables_obj["data_sources"][key] = ReportDataQuery.objects.get(
                        name=value
                    ).json_query
                except ReportDataQuery.DoesNotExist:
                    continue

    return yaml.dump(variables_obj)


def prep_variables_for_template(
    *,
    variables: str,
    dependencies: Dict[str, Any] = {},
    limit_query_results: Optional[int] = None,
) -> Dict[str, Any]:
    # replace any data queries in data_sources with the yaml
    variables = make_dataqueries_inline(variables=variables)

    # resolve dependencies that are agent, site, or client
    if "client" in dependencies.keys():
        Model = apps.get_model("clients", "Client")
        dependencies["client"] = Model.objects.get(id=dependencies["client"])
    elif "site" in dependencies.keys():
        Model = apps.get_model("clients", "Site")
        dependencies["site"] = Model.objects.get(id=dependencies["site"])
    elif "agent" in dependencies.keys():
        Model = apps.get_model("agents", "Agent")
        dependencies["agent"] = Model.objects.get(agent_id=dependencies["agent"])

    # check for variables that need to be replaced with the database values ({{client.name}}, {{agent.hostname}}, etc)
    if variables and isinstance(variables, str):
        # returns {{ model.prop }}, prop, model
        for string, model, prop in re.findall(RE_DB_VALUE, variables):
            value: Any = ""
            # will be agent, site, client, or global
            if model == "global":
                value = get_db_value(string=f"{model}.{prop}")
            elif model in dependencies.keys():
                instance = dependencies[model]
                value = (
                    get_db_value(string=prop, instance=instance) if instance else None
                )

            if value:
                variables = variables.replace(string, str(value))

    # check for any non-database dependencies and replace in variables
    if variables and isinstance(variables, str):
        RE_DEP_VALUE = re.compile(r"(\{\{\s*(.*)\s*\}\})")

        for string, dep in re.findall(RE_DEP_VALUE, variables):
            if dep in dependencies.keys():
                variables = variables.replace(string, str(dependencies[dep]))

    # load yaml variables if they exist
    variables = yaml.safe_load(variables) or {}

    # replace the data_sources with the actual data from DB. This will be passed to the template
    # in the form of {{data_sources.data_source_name}}
    if "data_sources" in variables.keys() and isinstance(
        variables["data_sources"], dict
    ):
        for key, value in variables["data_sources"].items():
            if isinstance(value, dict):
                data_source = value

                _ = data_source.pop("meta") if "meta" in data_source.keys() else None

                modified_datasource = resolve_model(data_source=data_source)
                queryset = build_queryset(
                    data_source=modified_datasource, limit=limit_query_results
                )
                variables["data_sources"][key] = queryset

    # generate and replace charts in the variables
    if "charts" in variables.keys() and isinstance(variables["charts"], dict):
        for key, chart in variables["charts"].items():
            # make sure chart options are present and a dict
            if "options" not in chart.keys() and not isinstance(chart["options"], dict):
                break

            options = chart["options"]
            # if data_frame is present and a str that means we need to replace it with a value from variables
            if "data_frame" in options.keys() and isinstance(
                options["data_frame"], str
            ):
                # dot dotation to datasource if exists
                data_source = options["data_frame"].split(".")
                data = variables
                for path in data_source:
                    if path in data.keys():
                        data = data[path]
                    else:
                        break

                if data:
                    chart["options"]["data_frame"] = data

            variables["charts"][key] = generate_chart(
                type=chart["chartType"],
                format=chart["outputType"],
                options=chart["options"],
                traces=chart["traces"] if "traces" in chart.keys() else None,
                layout=chart["layout"] if "layout" in chart.keys() else None,
            )

    return {**variables, **dependencies}


class ResolveModelException(Exception):
    pass


def resolve_model(*, data_source: Dict[str, Any]) -> Dict[str, Any]:
    tmp_data_source = data_source

    # check that model property is present and correct
    if "model" in data_source.keys():
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


ALLOWED_OPERATIONS = (
    # filtering
    "only",
    "defer",
    "filter",
    "exclude",
    "limit",
    "get",
    "first",
    "all",
    # custom fields
    "custom_fields",
    # presentation
    "json",
    # relations
    "select_related",
    "prefetch_related",
    # operations
    "aggregate",
    "annotate",
    "count",
    "values",
    # ordering
    "order_by",
)


class InvalidDBOperationException(Exception):
    pass


def build_queryset(*, data_source: Dict[str, Any], limit: Optional[int] = None) -> Any:
    local_data_source = data_source
    Model = local_data_source.pop("model")
    limit = limit
    count = False
    get = False
    first = False
    all = False
    isJson = False
    columns = local_data_source["only"] if "only" in local_data_source.keys() else None
    fields_to_add = []

    # create a base reporting queryset
    queryset = Model.objects.using("reporting")
    model_name = Model.__name__.lower()
    for operation, values in local_data_source.items():
        if operation not in ALLOWED_OPERATIONS:
            raise InvalidDBOperationException(
                f"DB operation: {operation} not allowed. Supported operations: only, defer, filter, get, first, all, custom_fields, exclude, limit, select_related, prefetch_related, annotate, aggregate, order_by, count"
            )

        if operation == "meta":
            continue
        elif operation == "custom_fields" and isinstance(values, list):
            from core.models import CustomField

            if model_name in ["client", "site", "agent"]:
                fields_to_add = [
                    field
                    for field in values
                    if CustomField.objects.filter(model=model_name, name=field).exists()
                ]

        elif operation == "limit":
            limit = values
        elif operation == "count":
            count = True
        elif operation == "get":
            get = True
        elif operation == "first":
            first = True
        elif operation == "all":
            all = True
        elif operation == "json":
            isJson = True
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
        if "id" not in columns:
            columns.append("id")
        queryset = queryset.values(*columns)
    else:
        queryset = queryset.values()

    if get or first:
        if get:
            queryset = queryset.get()
        elif first:
            queryset = queryset.first()

        if fields_to_add:
            return add_custom_fields(
                data=queryset,
                fields_to_add=fields_to_add,
                model_name=model_name,
                dict_value=True,
            )
        else:
            if isJson:
                return json.dumps(queryset, default=str)
            else:
                return queryset
    else:
        # add custom fields for list results
        if fields_to_add:
            return add_custom_fields(
                data=list(queryset), fields_to_add=fields_to_add, model_name=model_name
            )
        else:
            if isJson:
                return json.dumps(list(queryset), default=str)
            else:
                return list(queryset)


def add_custom_fields(
    *,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    fields_to_add: List[str],
    model_name: Literal["client", "site", "agent"],
    dict_value: bool = False,
):
    from core.models import CustomField
    from agents.models import AgentCustomField
    from clients.models import ClientCustomField, SiteCustomField

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


def normalize_asset_url(text: str, type: Literal["pdf", "html"]) -> str:
    RE_ASSET_URL = re.compile(
        r"(asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}))"
    )

    new_text = text
    for url, id in re.findall(RE_ASSET_URL, text):
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
    for _, id in re.findall(RE_ASSET_URL, template):
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
                added_ids.append(asset.id)
            except ReportAsset.DoesNotExist:
                continue

    return assets


def decode_base64_asset(asset: str) -> bytes:
    import base64

    return base64.b64decode(asset.encode("utf-8"))


def generate_chart(
    *,
    type: Literal["pie", "bar", "line"],
    format: Literal["html", "image"],
    options: Dict[str, Any],
    traces: Optional[Dict[str, Any]] = None,
    layout: Optional[Dict[str, Any]] = None,
) -> str:
    fig = getattr(px, type)(**options)

    if traces:
        fig.update_traces(**traces)

    if layout:
        fig.update_layout(**layout)

    if format == "html":
        return cast(str, fig.to_html(full_html=False, include_plotlyjs="cdn"))
    elif format == "image":
        return cast(str, fig.to_image(format="svg").decode("utf-8"))
