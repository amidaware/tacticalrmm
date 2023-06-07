"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from typing import Any, Dict, Tuple, Literal, Optional, Union, cast

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
# {{client.name}}, client.name, client
RE_DB_VALUE = re.compile(r"(\{\{\s*(client|site|agent|global)\.(.*)\s*\}\})")


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
    debug: bool = False,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    # validate the template before doing anything. This will throw a TemplateError exception
    env.parse(template)

    # convert template from markdown to html if type is markdown
    template_string = (
        Markdown.convert(template) if template_type == "markdown" else template
    )

    # replace any data queries in data_sources with the yaml
    variables = make_dataqueries_inline(variables)

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

    # append extends if html master template is configured
    if html_template:
        try:
            html_template_name = ReportHTMLTemplate.objects.get(pk=html_template).name

            template_string = (
                f"""{{% extends "{html_template_name}" %}}\n{template_string}"""
            )
        except ReportHTMLTemplate.DoesNotExist:
            pass

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
                queryset = build_queryset(data_source=modified_datasource, debug=debug)
                variables["data_sources"][key] = queryset

    # generate and replace charts in the variables
    if "charts" in variables.keys() and isinstance(variables["charts"], dict):
        for key, chart in variables["charts"].items():
            # make sure chart options are present and a dict
            if "options" not in chart.keys() and not isinstance(chart["options"], dict):
                break

            layout = None
            if "layout" in chart.keys():
                layout = chart["layout"]

            traces = None
            if "traces" in chart.keys():
                traces = chart["traces"]

            variables["charts"][key] = generate_chart(
                type=chart["chartType"],
                format=chart["outputType"],
                options=chart["options"],
                traces=traces,
                layout=layout,
            )

    tm = env.from_string(template_string)
    variables = {**variables, **dependencies}
    if variables:
        return (tm.render(css=css, **variables), variables)
    else:
        return (tm.render(css=css), None)


def make_dataqueries_inline(variables: str) -> str:
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


def build_queryset(*, data_source: Dict[str, Any], debug: bool = False) -> Any:
    local_data_source = data_source
    Model = local_data_source.pop("model")
    limit = None
    count = False
    get = False
    first = False
    all = False
    columns = local_data_source["only"] if "only" in local_data_source.keys() else None

    # create a base reporting queryset
    queryset = Model.objects.using("reporting")

    for operation, values in local_data_source.items():
        if operation not in ALLOWED_OPERATIONS:
            raise InvalidDBOperationException(
                f"DB operation: {operation} not allowed. Supported operations: only, defer, filter, get, first, all, exclude, limit, select_related, prefetch_related, annotate, aggregate, order_by, count"
            )

        if operation == "meta":
            continue
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

    if limit:
        queryset = queryset[:limit]

    if debug:
        queryset = queryset.values()

    if get:
        queryset = queryset.get()
    elif first:
        queryset = queryset.first()

    return queryset


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


def generate_chart(
    *,
    type: Literal["pie", "bar", "line"],
    format: Literal["html", "image"],
    options: Dict[str, Any],
    traces: Optional[Dict[str, Any]] = None,
    layout: Optional[Dict[str, Any]] = None,
) -> Union[str, bytes]:
    fig = getattr(px, type)(**options)

    if traces:
        fig.update_traces(**traces)

    if layout:
        fig.update_layout(**layout)

    if format == "html":
        return cast(str, fig.to_html(full_html=False, include_plotlyjs="cdn"))
    elif format == "image":
        return cast(bytes, fig.to_image(format="svg"))
