"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from unittest.mock import patch

import pytest
from agents.models import Agent
from django.apps import apps
from model_bakery import baker

from ..constants import REPORTING_MODELS
from ..utils import (
    InvalidDBOperationException,
    ResolveModelException,
    add_custom_fields,
    build_queryset,
    resolve_model,
)


class TestResolvingModels:
    def test_all_reporting_models_valid(self):
        for model_name, app_name in REPORTING_MODELS:
            try:
                apps.get_model(app_name, model_name)
            except LookupError:
                pytest.fail(f"Model: {model_name} does not exist in app: {app_name}")

    def test_resolve_model_valid_model(self):
        data_source = {"model": "Agent"}

        result = resolve_model(data_source=data_source)

        # Assuming 'agents.Agent' is a valid model in your Django app.
        from agents.models import Agent

        assert result["model"] == Agent

    def test_resolve_model_invalid_model_name(self):
        data_source = {"model": "InvalidModel"}

        with pytest.raises(
            ResolveModelException, match="Model lookup failed for InvalidModel"
        ):
            resolve_model(data_source=data_source)

    def test_resolve_model_no_model_key(self):
        data_source = {"key": "value"}

        with pytest.raises(
            ResolveModelException, match="Model key must be present on data_source"
        ):
            resolve_model(data_source=data_source)


@patch("agents.models.Agent.objects.using", return_value=Agent.objects.using("default"))
@pytest.mark.django_db()
class TestBuildingQueryset:
    @pytest.fixture
    def setup_agents(self):
        agent1 = baker.make("agents.Agent", hostname="ZAgent1", plat="windows")
        agent2 = baker.make("agents.Agent", hostname="Agent2", plat="windows")
        return [agent1, agent2]

    def test_build_queryset_with_valid_model(self, mock, setup_agents):
        data_source = {
            "model": Agent,
        }
        result = build_queryset(data_source=data_source)
        assert result is not None, "Queryset should not be None for a valid model."

    def test_build_queryset_invalid_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "invalid_op": "value",
        }
        with pytest.raises(InvalidDBOperationException):
            build_queryset(data_source=data_source)

    def test_build_queryset_without_model(self, mock, setup_agents):
        data_source = {}
        with pytest.raises(
            Exception
        ):  # This could be a more specific exception if you expect one.
            build_queryset(data_source=data_source)

    def test_build_queryset_only_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "only": ["hostname", "operating_system"]}

        result = build_queryset(data_source=data_source)

        assert len(result) == 2
        for agent_data in result:
            assert "hostname" in agent_data
            assert "operating_system" in agent_data
            assert "plat" not in agent_data

    def test_build_queryset_id_is_appended_if_only_exists(self, mock, setup_agents):
        data_source = {"model": Agent, "only": ["hostname"]}

        result = build_queryset(data_source=data_source)

        assert len(result) == 2
        for agent_data in result:
            assert "id" in agent_data

    def test_build_queryset_filter_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "filter": {"hostname": setup_agents[0].hostname},
        }

        result = build_queryset(data_source=data_source)

        assert len(result) == 1
        assert result[0]["hostname"] == setup_agents[0].hostname

    def test_filtering_operation_with_multiple_fields(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "filter": {
                "hostname": setup_agents[0].hostname,
                "operating_system": setup_agents[0].operating_system,
            },
        }

        result = build_queryset(data_source=data_source)

        assert len(result) == 1
        assert result[0]["hostname"] == setup_agents[0].hostname

    def test_filtering_with_non_existing_condition(self, mock, setup_agents):
        data_source = {"model": Agent, "filter": {"hostname": "doesn't exist"}}

        result = build_queryset(data_source=data_source)

        assert len(result) == 0

    def test_build_queryset_exclude_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "exclude": {"hostname": setup_agents[0].hostname},
        }

        results = build_queryset(data_source=data_source)

        assert len(results) == 1
        assert results[0]["hostname"] != setup_agents[0].hostname

    def test_build_query_get_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "get": {"agent_id": setup_agents[0].agent_id}}

        agent = build_queryset(data_source=data_source)
        assert agent["hostname"] == setup_agents[0].hostname

    def test_build_queryset_all_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "all": True,
        }
        result = build_queryset(data_source=data_source)
        assert len(result) == 2

    # test filter and only
    def test_build_queryset_filter_only_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "filter": {"hostname": setup_agents[0].hostname},
            "only": ["agent_id", "hostname"],
        }
        result = build_queryset(data_source=data_source)

        # should only return 1 result
        assert len(result) == 1
        assert result[0]["hostname"] == setup_agents[0].hostname
        assert "plat" not in result[0]

    def test_build_queryset_limit_operation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "limit": 1,
        }
        result = build_queryset(data_source=data_source)
        assert len(result) == 1

    def test_build_queryset_field_defer_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "defer": ["wmi_detail", "services"]}

        result = build_queryset(data_source=data_source)
        assert "wmi_detail" not in result[0]
        assert "services" not in result[0]
        assert result[0]["hostname"] == setup_agents[0].hostname

    def test_build_queryset_first_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "first": True}

        result = build_queryset(data_source=data_source)

        assert result["hostname"] == setup_agents[0].hostname

    def test_build_queryset_count_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "count": True}

        count = build_queryset(data_source=data_source)

        assert count == 2

    def test_build_queryset_order_by_operation(self, mock, setup_agents):
        data_source = {"model": Agent, "order_by": ["hostname"]}

        result = build_queryset(data_source=data_source)

        assert len(result) == 2
        assert result[0]["hostname"] == setup_agents[1].hostname
        assert result[1]["hostname"] == setup_agents[0].hostname

    def test_build_queryset_json_presentation(self, mock, setup_agents):
        import json

        data_source = {"model": Agent, "json": True}

        result = build_queryset(data_source=data_source)
        # Deserializing the result to check the content.
        result_data = json.loads(result)
        assert result_data[0]["hostname"] == setup_agents[0].hostname

    def test_build_queryset_csv_presentation(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "only": ["hostname", "operating_system"],
            "csv": True,
        }

        result = build_queryset(data_source=data_source)
        # should be a string in csv format
        assert isinstance(result, str)
        assert "hostname" in result.split("\n")[0]
        assert "operating_system" in result.split("\n")[0]

    def test_build_queryset_csv_presentation_rename_columns(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "only": ["hostname", "operating_system"],
            "csv": {"hostname": "Hostname", "operating_system": "Operating System"},
        }

        result = build_queryset(data_source=data_source)
        # should be a string in csv format
        assert isinstance(result, str)
        assert "Hostname" in result.split("\n")[0]
        assert "Operating System" in result.split("\n")[0]

    def test_build_queryset_custom_fields(self, mock, setup_agents):
        default_value = "Default Value"

        field1 = baker.make(
            "core.CustomField", name="custom_1", model="agent", type="text"
        )
        baker.make(
            "core.CustomField",
            name="custom_2",
            model="agent",
            type="text",
            default_value_string=default_value,
        )

        baker.make(
            "agents.AgentCustomField",
            agent=setup_agents[0],
            field=field1,
            string_value="Agent1",
        )
        baker.make(
            "agents.AgentCustomField",
            agent=setup_agents[1],
            field=field1,
            string_value="Agent2",
        )

        data_source = {"model": Agent, "custom_fields": ["custom_1", "custom_2"]}

        result = build_queryset(data_source=data_source)
        assert len(result) == 2

        # check agent 1
        assert result[0]["custom_fields"]["custom_1"] == "Agent1"
        assert result[0]["custom_fields"]["custom_2"] == default_value

        # check agent 2
        assert result[1]["custom_fields"]["custom_1"] == "Agent2"
        assert result[1]["custom_fields"]["custom_2"] == default_value

    def test_build_queryset_filter_only_json_combination(self, mock, setup_agents):
        import json

        data_source = {
            "model": Agent,
            "filter": {"agent_id": setup_agents[0].agent_id},
            "only": ["hostname", "agent_id"],
            "json": True,
        }

        result_json = build_queryset(data_source=data_source)
        result = json.loads(result_json)

        assert len(result) == 1
        assert "operating_system" not in result[0]
        assert result[0]["hostname"] == setup_agents[0].hostname

    def test_build_queryset_get_only_json_combination(self, mock, setup_agents):
        import json

        data_source = {
            "model": Agent,
            "get": {"agent_id": setup_agents[0].agent_id},
            "only": ["hostname", "agent_id"],
            "json": True,
        }

        result_json = build_queryset(data_source=data_source)
        result = json.loads(result_json)

        assert isinstance(result, dict)
        assert "operating_system" not in result
        assert result["hostname"] == setup_agents[0].hostname

    def test_build_queryset_filter_order_by_combination(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "filter": {"plat": "windows"},
            "order_by": ["hostname"],
        }

        result = build_queryset(data_source=data_source)

        assert len(result) == 2
        assert result[0]["hostname"] == setup_agents[1].hostname
        assert result[1]["hostname"] == setup_agents[0].hostname

    def test_build_queryset_defer_used_over_only(self, mock, setup_agents):
        data_source = {
            "model": Agent,
            "only": ["hostname", "operating_system"],
            "defer": ["operating_system"],
        }

        result = build_queryset(data_source=data_source)[0]

        assert "hostname" in result
        assert "operating_system" not in result

    def test_build_queryset_limit_ignored_with_first_or_get(self, mock, setup_agents):
        data_source = {"model": Agent, "limit": 1, "first": True}

        result_first = build_queryset(data_source=data_source)
        assert isinstance(result_first, dict)

        data_source = {
            "model": Agent,
            "limit": 1,
            "get": {"agent_id": setup_agents[0].agent_id},
        }

        result_get = build_queryset(data_source=data_source)
        assert isinstance(result_get, dict)

    def test_build_queryset_result_type_with_get_or_first(self, mock, setup_agents):
        # Test with "get"
        data_source_get = {
            "model": Agent,
            "get": {"hostname": setup_agents[0].hostname},
        }
        result_get = build_queryset(data_source=data_source_get)

        # Test with "first"
        data_source_first = {"model": Agent, "first": True}
        result_first = build_queryset(data_source=data_source_first)

        assert not isinstance(result_get, list)
        assert not isinstance(result_first, list)

    def test_build_queryset_result_type_without_get_or_first(self, mock, setup_agents):
        data_source = {
            "model": Agent,
        }

        result = build_queryset(data_source=data_source)

        assert isinstance(result, list)

    def test_build_queryset_result_in_json_format(self, mock, setup_agents):
        import json

        data_source = {"model": Agent, "json": True}

        result = build_queryset(data_source=data_source)

        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError:
            assert False

        assert isinstance(parsed_result, list)


@pytest.mark.django_db
class TestAddingCustomFields:
    @pytest.mark.parametrize(
        "model_name,custom_field_model",
        [
            ("agent", "agents.AgentCustomField"),
            ("client", "clients.ClientCustomField"),
            ("site", "clients.SiteCustomField"),
        ],
    )
    def test_add_custom_fields_with_list_of_dicts(self, model_name, custom_field_model):
        custom_field = baker.make("core.CustomField", name="field1", model=model_name)
        default_value = "Default Value"
        baker.make(
            "core.CustomField",
            name="field2",
            model=model_name,
            default_value_string=default_value,
        )

        custom_model_instance1 = baker.make(
            custom_field_model, field=custom_field, string_value="Value"
        )
        custom_model_instance2 = baker.make(
            custom_field_model, field=custom_field, string_value="Value"
        )

        data = [
            {"id": getattr(custom_model_instance1, f"{model_name}_id")},
            {"id": getattr(custom_model_instance2, f"{model_name}_id")},
        ]
        fields_to_add = ["field1", "field2"]
        result = add_custom_fields(
            data=data, fields_to_add=fields_to_add, model_name=model_name
        )

        # Assert logic here based on what you expect the result to be
        assert result[0]["custom_fields"]["field1"] == custom_model_instance1.value
        assert result[1]["custom_fields"]["field1"] == custom_model_instance2.value

        assert result[0]["custom_fields"]["field2"] == default_value
        assert result[1]["custom_fields"]["field2"] == default_value

    @pytest.mark.parametrize(
        "model_name,custom_field_model",
        [
            ("agent", "agents.AgentCustomField"),
            ("client", "clients.ClientCustomField"),
            ("site", "clients.SiteCustomField"),
        ],
    )
    def test_add_custom_fields_to_dictionary(self, model_name, custom_field_model):
        custom_field = baker.make("core.CustomField", name="field1", model=model_name)
        custom_model_instance = baker.make(
            custom_field_model, field=custom_field, string_value="default_value"
        )

        data = {"id": getattr(custom_model_instance, f"{model_name}_id")}
        fields_to_add = ["field1"]
        result = add_custom_fields(
            data=data,
            fields_to_add=fields_to_add,
            model_name=model_name,
            dict_value=True,
        )

        # Assert logic here based on what you expect the result to be
        assert result["custom_fields"]["field1"] == custom_model_instance.value

    @pytest.mark.parametrize(
        "model_name",
        [
            "agent",
            "client",
            "site",
        ],
    )
    def test_add_custom_fields_with_default_value(self, model_name):
        default_value = "default_value"
        baker.make(
            "core.CustomField",
            name="field1",
            model=model_name,
            default_value_string=default_value,
        )

        # Note: Not creating an instance of the custom_field_model here to ensure the default value is used

        data = {"id": 999}  # ID not associated with any custom field model instance
        fields_to_add = ["field1"]
        result = add_custom_fields(
            data=data,
            fields_to_add=fields_to_add,
            model_name=model_name,
            dict_value=True,
        )

        # Assert that the default value is used
        assert result["custom_fields"]["field1"] == default_value
