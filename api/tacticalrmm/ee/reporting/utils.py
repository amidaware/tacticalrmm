"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import yaml
import re
import pandas as pd

from django.apps import apps
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from jinja2 import Environment, FunctionLoader
from typing import Dict, Any, Literal, Union
from .markdown.config import Markdown
from .models import ReportHTMLTemplate, ReportTemplate, ReportAsset
from .constants import REPORTING_MODELS

from tacticalrmm.utils import get_db_value


# regex for db data replacement
# will return 3 groups of matches in a tuple when uses with re.findall
# {{client.name}}, client.name, client
RE_DB_VALUE = re.compile(r'(\{\{\s*(client|site|agent|global)\.(.*)\s*\}\})')


# this will lookup the Jinja parent template in the DB
# Example: {% extends "MASTER_TEMPLATE_NAME or REPORT_TEMPLATE_NAME" %}
def db_template_loader(template_name):
    # trys the ReportHTMLTemplate table and ReportTemplate table
    try:
        return ReportHTMLTemplate.objects.get(name=template_name).html
    except ReportHTMLTemplate.DoesNotExist:
        pass

    try:
        template = ReportTemplate.objects.get(name=template_name)
        return template.template_html if template.type == "html" else template.template_md
    except ReportHTMLTemplate.DoesNotExist:
        pass

    return None

# sets up Jinja environment wiht the db loader template
# comment tags needed to be editted because they conflicted with css properties
env = Environment(
    loader=FunctionLoader(db_template_loader),
    comment_start_string='{=',
    comment_end_string='=}',
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
    html_template: int = None,
    variables: str = "",
    dependencies: Dict[str, int] = {}
) -> str:
    
    # convert template from markdown to html if type is markdown
    template_string = Markdown.convert(template) if template_type == "markdown" else template

    # check for variables that need to be replaced with the database values ({{client.name}}, {{agent.hostname}}, etc)
    if variables and isinstance(variables, str):
        # returns {{ model.prop }}, prop, model
        for string, model, prop in re.findall(RE_DB_VALUE, variables):
            value = ""
            # will be agent, site, client, or global
            if model == "global":
                value = get_db_value(string=f"{model}.{prop}")
            elif model in ["client", "site", "agent"]:
                if model == "client" and "client" in dependencies.keys():
                    Model = apps.get_model("clients", "Client")
                    instance = Model.objects.get(id=dependencies["client"])
                elif model == "site"  and "site" in dependencies.keys():
                    Model = apps.get_model("clients", "Site")
                    instance = Model.objects.get(id=dependencies["site"])
                elif model == "agent" and "agent" in dependencies.keys():
                    Model = apps.get_model("agents", "Agent")
                    instance = Model.objects.get(agent_id=dependencies["agent"])
                else:
                    instance = None

                value = get_db_value(string=prop, instance=instance) if instance else None
            if value:
                variables = variables.replace(string, str(value))

    # load yaml variables if they exist
    variables = yaml.safe_load(variables) or {}

    # append extends if html master template is configured
    if html_template:
        try:
            html_template_name = ReportHTMLTemplate.objects.get(pk=html_template).name

            template_string = f"""{{% extends "{html_template_name}" %}}\n{template_string}"""
        except ReportHTMLTemplate.DoesNotExist:
            pass

    # replace the data_sources with the actual data from DB. This will be passed to the template
    # in the form of {{data_sources.data_source_name}}
    if "data_sources" in variables.keys() and isinstance(variables["data_sources"], dict):
        for key, value in variables["data_sources"].items():

            data_source = {}
            # data_source is referencing a saved data query
            if isinstance(value, str):
                ReportDataQuery = apps.get_model("reporting", "ReportDataQuery")
                try:
                    data_source = ReportDataQuery.objects.get(
                        name=value
                    ).json_query
                except ReportDataQuery.DoesNotExist:
                    continue

            # inline data source
            elif isinstance(value, dict):
                data_source = value

            _ = data_source.pop("meta") if "meta" in data_source.keys() else None

            modified_datasource = resolve_model(data_source=data_source)
            queryset = build_queryset(data_source=modified_datasource)
            variables["data_sources"][key] = queryset

    # generate and replace charts in the variables
    if "charts" in variables.keys() and isinstance(variables["charts"], dict):
        for key, chart in variables["charts"].items():
            
            # make sure chart options are present and a dict
            if "options" not in chart.keys() and not isinstance(chart["options"], dict):
                break

            options = chart["options"]
            # if data_frame is present and a str that means we need to replace it with a value from variables
            if "data_frame" in options.keys() and isinstance(options["data_frame"], str):
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

            layout = None
            if "layout" in chart.keys():
                layout = chart["layout"]

            traces = None
            if "traces" in chart.keys():
                traces = chart["traces"]

            variables["charts"][key] = generate_chart(type=chart["chartType"], format=chart["outputType"], options=chart["options"], traces=traces, layout=layout)

    tm = env.from_string(template_string)
    variables = {**variables, **dependencies}
    if variables:
        return tm.render(css=css, **variables)
    else:
        return tm.render(css=css)


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
    # relations
    "select_related",
    "prefetch_related",
    # operations
    "aggregate",
    "annotate",
    "count",
    # ordering
    "order_by",
)


class InvalidDBOperationException(Exception):
    pass


def build_queryset(*, data_source: Dict[str, Any]) -> Any:
    local_data_source = data_source
    Model = local_data_source.pop("model")
    limit = None
    count = None
    columns = local_data_source["only"] if "only" in local_data_source.keys() else None

    # create a base reporting queryset
    queryset = Model.objects.using("reporting")

    for operation, values in local_data_source.items():
        if operation not in ALLOWED_OPERATIONS:
            raise InvalidDBOperationException(
                f"DB operation: {operation} not allowed. Supported operations: only, defer, filter, exclude, limit, select_related, prefetch_related, annotate, aggregate, order_by, count"
            )

        if operation == "meta":
            continue
        elif operation == "limit":
            limit = values
        elif operation == "count":
            count = True
        elif isinstance(values, list):
            queryset = getattr(queryset, operation)(*values)
        elif isinstance(values, dict):
            queryset = getattr(queryset, operation)(**values)
        else:
            queryset = getattr(queryset, operation)(values)

    if count:
        return queryset.count()
    
    if limit:
        queryset = queryset[:limit]

    if columns:
        queryset = queryset.values(*columns)
    else:
        queryset = queryset.values()

    return queryset


def normalize_asset_url(text: str, type: Literal["pdf", "html"]):
    RE_ASSET_URL = re.compile(r"(asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}))")

    new_text = text
    for url, id in re.findall(RE_ASSET_URL,text):
        try:
            asset = ReportAsset.objects.get(id=id)
            if type == "html":
                new_text = new_text.replace(f"asset://{id}", f"{asset.file.url}?id={id}")
            else:
                new_text = new_text.replace(f"{url}", f"file://{asset.file.path}")
        except ReportAsset.DoesNotExist:
            pass

    return new_text

def generate_chart(*, type: Literal["pie", "bar", "line"], format: Literal["html", "image"], options: Dict[str, Any], traces: Dict[str, Any] = None, layout: Dict[str, Any] = None) -> Union[str, bytes]:
    import plotly.express as px

    fig = getattr(px, type)(**options)

    if traces:
        fig.update_traces(**traces)

    if layout:
        fig.update_layout(**layout)

    if format == "html":
        return fig.to_html(full_html=False, include_plotlyjs="cdn")
    elif format == "image":
        return fig.to_image(format="svg")
    