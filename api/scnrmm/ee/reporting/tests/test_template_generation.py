"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import pytest
from model_bakery import baker

from ..utils import db_template_loader, generate_html


@pytest.mark.django_db
class TestGenerateHTML:
    @pytest.fixture
    def base_template(self):
        html = "<html>{% block content %}{% endblock %}</html>"
        return baker.make(
            "reporting.ReportHTMLTemplate", name="Base Template", html=html
        )

    def test_markdown_conversion(self):
        template = "# This is a header"
        result, _ = generate_html(
            template=template, template_type="markdown", css="", variables=""
        )
        assert "<h1>This is a header</h1>" in result

    def test_html_unchanged(self):
        template = "<h1>This is a header</h1>"
        result, _ = generate_html(
            template=template, template_type="html", css="", variables=""
        )
        assert "<h1>This is a header</h1>" in result

    def test_html_template_exists(self, base_template):
        template = "{% block content %}<h1>This is a header</h1>{% endblock %}"
        result, _ = generate_html(
            template=template,
            template_type="html",
            html_template=base_template.id,
            css="",
            variables="",
        )

        assert "<html><h1>This is a header</h1></html>" == result

    def test_html_template_does_not_exist(self):
        template = "<h1>This is a header</h1>"
        # check it doesn't raise an error.
        generate_html(
            template=template,
            template_type="html",
            html_template=999,
            css="",
            variables="",
        )

    def test_variables_processing(self):
        template = "Hello {{ name }}"
        variables = "name: John"
        result, _ = generate_html(
            template=template, template_type="html", css="", variables=variables
        )

        assert "Hello John" in result

    def test_css_incorporation(self):
        template = "<html><head><style>{{css}}</style></head></html>"
        css = ".my-class { color: red; }"
        result, _ = generate_html(
            template=template, template_type="html", css=css, variables=""
        )
        assert css in result


@pytest.mark.django_db
class TestJinjaDBLoader:
    @pytest.fixture
    def report_base_template(self):
        return baker.make(
            "reporting.ReportHTMLTemplate", name="test_html_template", html="Test HTML"
        )

    @pytest.fixture
    def report_template(self):
        return baker.make(
            "reporting.ReportTemplate", name="test_md_template", template_md="Test MD"
        )

    def test_load_base_template(self, report_base_template):
        result = db_template_loader(report_base_template.name)
        assert result == "Test HTML"

    def test_fallback_to_md_template(self, report_template):
        result = db_template_loader(report_template.name)
        assert result == "Test MD"

    def test_no_template_found(self):
        # Will return None
        result = db_template_loader("nonexistent_template")
        assert result is None

    def test_html_template_priority(self):
        # Create both a ReportHTMLTemplate and a ReportTemplate with the same name
        template_name = "common_template"
        baker.make("reporting.ReportHTMLTemplate", name=template_name, html="Test HTML")
        baker.make(
            "reporting.ReportTemplate", name=template_name, template_md="Test MD"
        )

        result = db_template_loader(template_name)
        assert result == "Test HTML"  # HTML has priority
