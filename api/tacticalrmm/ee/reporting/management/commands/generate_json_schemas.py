"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""
import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings as djangosettings
from ...constants import REPORTING_MODELS


class Command(BaseCommand):
    help = "Generate JSON Schemas"

    def handle(self, *args, **kwargs) -> None:
        generate_schema()


def generate_schema() -> None:
    oneOf = list()

    for model, app in REPORTING_MODELS:
        Model = apps.get_model(app_label=app, model_name=model)

        fields = Model._meta.get_fields()

        order_by = []
        for field in fields:
            order_by.append(field.name)
            order_by.append(f"-{field.name}")

        filterObj = {}
        patternObj = {}
        select_related = []

        for field in fields:
            field_type = field.get_internal_type()

            if field_type == "CharField" and field.choices:
                propDefinition = {
                    "type": "string",
                    "enum": [index for index, _ in field.choices],
                }
            elif field_type == "BooleanField":
                propDefinition = {
                    "type": "boolean",
                }
            elif field.many_to_many or field.one_to_many:
                continue
            elif (
                field_type == "ForeignKey"
                or field.name == "id"
                or "Integer" in field_type
            ):
                propDefinition = {
                    "type": "integer",
                }

                if field_type == "ForeignKey":
                    select_related.append(field.name)

            else:
                propDefinition = {
                    "type": "string",
                }

            filterObj[field.name] = propDefinition
            patternObj["^" + field.name + "(_{1,2}[a-zA-Z]+)*$"] = propDefinition

        oneOf.append(
            {
                "properties": {
                    "model": {"type": "string", "enum": [model.lower()]},
                    "filter": {
                        "type": "object",
                        "properties": filterObj,
                        "patternProperties": patternObj,
                        "additionalProperties": False,
                    },
                    "get": {
                        "type": "object",
                        "properties": filterObj,
                        "patternProperties": patternObj,
                        "additionalProperties": False,
                    },
                    "exclude": {
                        "type": "object",
                        "properties": filterObj,
                        "patternProperties": patternObj,
                        "additionalProperties": False,
                    },
                    "defer": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minimum": 1,
                            "enum": [field.name for field in fields],
                        },
                    },
                    "only": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minimum": 1,
                            "anyOf": [
                                {"pattern": "^" + field.name + "(_{1,2}[a-zA-Z]+)*$"}
                                for field in fields
                            ],
                        },
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
            "limit": {"type": "integer"},
            "count": {"type": "boolean"}
        },
        "required": ["model"],
        "oneOf": oneOf,
    }

    with open(
        f"{djangosettings.STATICFILES_DIRS[0]}reporting/schemas/query_schema.json", "w"
    ) as outfile:
        outfile.write(json.dumps(schema, indent=4))
