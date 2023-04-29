"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from rest_framework import status
from rest_framework.response import Response
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from jinja2 import Template
from .markdown.config import Markdown
from typing import Optional


default_template = """
<html>
    <head>
        <style>
        {{ css }}
        </style>
    </head>

    <body>
        {{ body }}
    </body>
</html>
"""


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
    html_template: Optional[str] = None
) -> str:
    tm = Template(html_template if html_template else default_template)
    html_report = tm.render(
        css=css,
        body=Markdown.convert(template) if template_type == "markdown" else template,
    )

    return html_report


def notify_error(msg: str) -> Response:
    return Response(msg, status=status.HTTP_400_BAD_REQUEST)
