"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from django.apps import apps
from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

from ...constants import REPORTING_MODELS

if TYPE_CHECKING:
    from django.db.models import Model


class Command(BaseCommand):
    help = "Generate JSON Schemas"

    def handle(self, *args: Tuple[Any, Any], **kwargs: Dict[str, Any]) -> None:
        generate_schema()


# recursive function to traverse foreign keys and get values
def traverse_model_fields(
    *, model: "Model", prefix: str = "", depth: int = 3
) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], List[str]]:
    filterObj: Dict[str, Any] = {}
    patternObj: Dict[str, Any] = {}
    select_related: List[str] = []
    field_list: List[str] = []

    if depth < 1:
        return filterObj, patternObj, select_related, field_list
    for field in model._meta.get_fields():
        field_type = field.get_internal_type()  # type: ignore
        if field_type == "CharField" and field.choices:  # type: ignore
            propDefinition = {
                "type": "string",
                "enum": [index for index, _ in field.choices],  # type: ignore
            }
        elif field_type == "BooleanField":
            propDefinition = {
                "type": "boolean",
            }
        elif field.many_to_many or field.one_to_many:
            continue
        elif (
            field_type == "ForeignKey" or field.name == "id" or "Integer" in field_type
        ):
            propDefinition = {
                "type": "integer",
            }
            if field_type == "ForeignKey":
                select_related.append(prefix + field.name)
                related_model = field.related_model
                # Get fields of the related model, recursively
                filter, pattern, select, list = traverse_model_fields(
                    model=related_model,  # type: ignore
                    prefix=prefix + field.name + "__",
                    depth=depth - 1,
                )
                filterObj = {**filterObj, **filter}
                patternObj = {**patternObj, **pattern}
                select_related += select
                field_list += list
        else:
            propDefinition = {
                "type": "string",
            }
        filterObj[prefix + field.name] = propDefinition
        patternObj["^" + prefix + field.name + "(__[a-zA-Z]+)*$"] = propDefinition
        field_list.append(prefix + field.name)
    return filterObj, patternObj, select_related, field_list


def generate_schema() -> None:
    oneOf = []

    for model, app in REPORTING_MODELS:
        Model = apps.get_model(app_label=app, model_name=model)

        filterObj, patternObj, select_related, field_list = traverse_model_fields(
            model=Model, depth=3
        )

        order_by = []
        for field in field_list:
            order_by.append(field)
            order_by.append(f"-{field}")

        oneOf.append(
            {
                "properties": {
                    "model": {"type": "string", "enum": [model.lower()]},
                    "filter": {
                        "type": "object",
                        "properties": filterObj,
                        "patternProperties": patternObj,
                    },
                    "exclude": {
                        "type": "object",
                        "properties": filterObj,
                        "patternProperties": patternObj,
                    },
                    "defer": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minimum": 1,
                            "enum": field_list,
                        },
                    },
                    "only": {
                        "type": "array",
                        "items": {"type": "string", "minimum": 1, "enum": field_list},
                    },
                    "select_related": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minimum": 1,
                            "enum": select_related,
                        },
                    },
                    "order_by": {"type": "string", "enum": order_by},
                },
            }
        )

    schema = {
        "$id": f"https://{djangosettings.ALLOWED_HOSTS[0]}/static/reporting/schemas/query_schema.json",
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "enum": [model.lower() for model, _ in REPORTING_MODELS],
            },
            "custom_fields": {
                "type": "array",
                "items": {"type": "string", "minimum": 1},
            },
            "limit": {"type": "integer"},
            "count": {"type": "boolean"},
            "get": {"type": "boolean"},
            "first": {"type": "boolean"},
        },
        "required": ["model"],
        "oneOf": oneOf,
    }

    with open(
        f"{djangosettings.STATICFILES_DIRS[0]}reporting/schemas/query_schema.json", "w"
    ) as outfile:
        outfile.write(json.dumps(schema))
