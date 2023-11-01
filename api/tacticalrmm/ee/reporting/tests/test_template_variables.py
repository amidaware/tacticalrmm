"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from unittest.mock import patch

import pytest
from model_bakery import baker

from ..utils import (
    prep_variables_for_template,
    process_chart_variables,
    process_data_sources,
    process_dependencies,
)


@pytest.mark.django_db
class TestProcessingDependencies:
    # Fixtures for creating model instances
    @pytest.fixture
    def test_client(db):
        return baker.make("clients.Client", name="Test Client Name")

    @pytest.fixture
    def test_site(db):
        return baker.make("clients.Site", name="Test Site Name")

    @pytest.fixture
    def test_agent(db):
        return baker.make(
            "agents.Agent", agent_id="Test Agent ID", hostname="Test Agent Name"
        )

    @pytest.fixture
    def test_global(db):
        return baker.make(
            "core.GlobalKVStore", name="some_global_value", value="Some Global Value"
        )

    def test_replace_with_client_db_value(self, test_client):
        variables = """
        some_field:
            client_field: {{client.name}}
        """
        dependencies = {"client": test_client.id}
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["client_field"] == test_client.name

    def test_replace_with_site_db_value(self, test_site):
        variables = """
        some_field:
            site_field: {{site.name}}
        """
        dependencies = {"site": test_site.id}
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["site_field"] == test_site.name

    def test_replace_with_agent_db_value(self, test_agent):
        variables = """
        some_field:
            agent_field: {{agent.hostname}}
        """
        dependencies = {"agent": test_agent.agent_id}
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["agent_field"] == test_agent.hostname

    def test_replace_with_global_value(self, test_global):
        variables = """
        some_field:
            global_field: {{global.some_global_value}}
        """
        result = process_dependencies(variables=variables, dependencies={})
        # Assuming you have a global value with key 'some_global_value' set to 'Some Global Value'
        assert result["some_field"]["global_field"] == test_global.value

    def test_replace_with_non_db_dependencies(self):
        variables = """
        some_field:
            dependency_field: {{some_dependency}}
        """
        dependencies = {"some_dependency": "Some Value"}
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["dependency_field"] == "Some Value"

    def test_missing_non_db_dependencies(self):
        variables = """
        some_field:
            missing_dependency: "{{missing_dependency}}"
        """
        dependencies = {}  # Empty dependencies, simulating a missing dependency
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["missing_dependency"] == "{{missing_dependency}}"

    def test_variables_dependencies_merge(self, test_agent):
        variables = """
        some_field:
            agent_field: {{agent.agent_id}}
            dependency_field: {{some_dependency}}
        """
        dependencies = {"agent": test_agent.agent_id, "some_dependency": "Some Value"}
        result = process_dependencies(variables=variables, dependencies=dependencies)
        assert result["some_field"]["agent_field"] == "Test Agent ID"
        assert result["some_field"]["dependency_field"] == "Some Value"
        # Additionally, assert the merged structure has both processed variables and dependencies
        assert "agent" in result
        assert isinstance(result["agent"], type(test_agent))
        assert "some_dependency" in result
        assert result["some_dependency"] == "Some Value"

    def test_multiple_replacements(self, test_agent, test_client, test_site):
        variables = """
        fields:
            agent_name: {{agent.hostname}}
            client_name: {{client.name}}
            site_name: {{site.name}}
            dependency_1: {{dep_1}}
            dependency_2: {{dep_2}}
        """

        dependencies = {
            "agent": test_agent.agent_id,
            "client": test_client.id,
            "site": test_site.id,
            "dep_1": "Dependency Value 1",
            "dep_2": "Dependency Value 2",
        }

        result = process_dependencies(variables=variables, dependencies=dependencies)

        assert result["fields"]["agent_name"] == test_agent.hostname
        assert result["fields"]["client_name"] == test_client.name
        assert result["fields"]["site_name"] == test_site.name
        assert result["fields"]["dependency_1"] == "Dependency Value 1"
        assert result["fields"]["dependency_2"] == "Dependency Value 2"

        # Also verify that the non-replaced fields from dependencies are present in the result.
        assert "agent" in result
        assert "client" in result
        assert "site" in result
        assert result["dep_1"] == "Dependency Value 1"
        assert result["dep_2"] == "Dependency Value 2"


@pytest.mark.django_db
class TestProcessDataSourceVariables:
    def test_process_data_sources_without_data_sources(self):
        variables = {"other_key": "some_value"}
        result = process_data_sources(variables=variables)
        assert result == variables

    def test_process_data_sources_with_non_dict_data_sources(self):
        variables = {"data_sources": "some_string_value"}
        result = process_data_sources(variables=variables)
        assert result == variables

    def test_process_data_sources_with_dict_data_sources(self):
        variables = {
            "data_sources": {
                "source1": {"model": "agent", "other_field": "value"},
                "source2": "some_string_value",
            }
        }

        mock_queryset = {"data": "sample_data"}

        # Mock build_queryset to return the mock_queryset
        with patch("ee.reporting.utils.build_queryset", return_value=mock_queryset):
            result = process_data_sources(variables=variables)

            # Assert that the data_sources for "source1" is replaced with mock_queryset
            assert result["data_sources"]["source1"] == mock_queryset

            # Assert that the "source2" data remains unchanged
            assert result["data_sources"]["source2"] == "some_string_value"


class TestProcessChartVariables:
    def test_process_chart_no_replace_data_frame(self):
        # Scenario where path doesn't exist in variables
        variables = {
            "charts": {
                "chart1": {
                    "chartType": "type1",
                    "outputType": "html",
                    "options": {"data_frame": "path.to.nonexistent"},
                }
            }
        }

        assert process_chart_variables(variables=variables) == variables

    def test_process_chart_generate_chart_invocation(self):
        # Ensure generate_chart is invoked with expected parameters
        variables = {
            "charts": {
                "chart1": {
                    "chartType": "type1",
                    "outputType": "html",
                    "options": {},
                    "traces": "Some Traces",
                    "layout": "Some Layout",
                }
            }
        }
        with patch("ee.reporting.utils.generate_chart") as mock_generate_chart:
            mock_generate_chart.return_value = "<html>Chart Here</html>"
            _ = process_chart_variables(variables=variables)

        mock_generate_chart.assert_called_once_with(
            type="type1",
            format="html",
            options={},
            traces="Some Traces",
            layout="Some Layout",
        )

    def test_process_chart_missing_keys(self):
        # Scenario where necessary keys are missing
        variables = {"charts": {"chart1": {}}}

        result = process_chart_variables(variables=variables)
        assert result == variables  # Expecting unchanged variables

    def test_process_chart_no_charts(self):
        # Scenario with no charts key or charts not a dict
        variables1 = {}
        variables2 = {"charts": "Not a dict"}

        assert process_chart_variables(variables=variables1) == variables1
        assert process_chart_variables(variables=variables2) == variables2

    def test_process_chart_replaces_data_frame(self):
        # Sample input
        variables = {
            "charts": {
                "myChart": {
                    "chartType": "bar",
                    "outputType": "html",
                    "options": {"data_frame": "data_sources.sample_data"},
                }
            },
            "data_sources": {"sample_data": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]},
        }

        with patch("ee.reporting.utils.generate_chart") as mock_generate_chart:
            mock_generate_chart.return_value = "<html>Chart Here</html>"

            result = process_chart_variables(variables=variables)

        # Check if the generate_chart function was called correctly
        mock_generate_chart.assert_called_once_with(
            type="bar",
            format="html",
            options={"data_frame": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]},
            traces=None,
            layout=None,
        )

        # Check if the returned data has the chart in place
        assert "<html>Chart Here</html>" in result["charts"]["myChart"]


class TestPrepVariablesFunction:
    def test_prep_variables_base(self):
        result = prep_variables_for_template(variables="")
        assert isinstance(result, dict)
        assert not result

    def test_prep_variables_with_dependencies(self):
        with patch(
            "ee.reporting.utils.process_dependencies",
            return_value={"dependency_key": "dependency_value"},
        ):
            result = prep_variables_for_template(
                variables="", dependencies={"some_dependency": "value"}
            )
            assert "dependency_key" in result
            assert result["dependency_key"] == "dependency_value"

    def test_prep_variables_with_data_sources(self):
        with patch(
            "ee.reporting.utils.process_data_sources",
            return_value={"data_source_key": "data_value"},
        ):
            result = prep_variables_for_template(variables="data_sources: some_data")
            assert "data_source_key" in result
            assert result["data_source_key"] == "data_value"

    def test_prep_variables_with_charts(self):
        with patch(
            "ee.reporting.utils.process_chart_variables",
            return_value={"chart_key": "chart_value"},
        ):
            result = prep_variables_for_template(variables="charts: some_chart")
            assert "chart_key" in result
            assert result["chart_key"] == "chart_value"
