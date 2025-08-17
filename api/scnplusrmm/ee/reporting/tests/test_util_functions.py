"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import base64

import pytest
from model_bakery import baker

from ..utils import base64_encode_assets, decode_base64_asset, normalize_asset_url


@pytest.mark.django_db
class TestBase64EncodeDecodeAssets:
    def test_base64_encode_assets_multiple_valid_urls(self):
        asset1 = baker.make("reporting.ReportAsset", _create_files=True)
        asset2 = baker.make("reporting.ReportAsset", _create_files=True)
        template = f"Some content with link asset://{asset1.id} and another link asset://{asset2.id}"

        result = base64_encode_assets(template)

        assert len(result) == 2

        # check asset 1
        assert result[0]["id"] == asset1.id
        # Checking if the file content is correctly encoded to base64
        encoded_content = base64.b64encode(asset1.file.file.read()).decode("utf-8")
        assert result[0]["file"] == encoded_content

        # check asset 2
        assert result[1]["id"] == asset2.id
        # Checking if the file content is correctly encoded to base64
        encoded_content = base64.b64encode(asset2.file.file.read()).decode("utf-8")
        assert result[1]["file"] == encoded_content

    def test_base64_encode_assets_some_invalid_urls(self):
        asset = baker.make("reporting.ReportAsset", _create_files=True)
        invalid_id = "11111111-1111-1111-1111-111111111111"
        template = f"Some content with link asset://{asset.id} and invalid link asset://{invalid_id}"

        result = base64_encode_assets(template)

        assert len(result) == 1
        assert result[0]["id"] == asset.id

    def test_base64_encode_assets_no_urls(self):
        template = "Some content with no assets"
        result = base64_encode_assets(template)
        assert result == []

    def test_base64_encode_assets_duplicate_urls(self):
        asset = baker.make("reporting.ReportAsset", _create_files=True)
        template = f"Some content with link asset://{asset.id} and another link asset://{asset.id}"

        result = base64_encode_assets(template)

        assert len(result) == 1
        assert result[0]["id"] == asset.id

    def test_decode_base64_asset_valid_input(self):
        original_data = b"Hello, world!"
        encoded_data = base64.b64encode(original_data).decode("utf-8")

        result = decode_base64_asset(encoded_data)

        assert result == original_data

    def test_decode_base64_asset_invalid_input(self):
        invalid_data = "Not a base64 encoded string."

        with pytest.raises(base64.binascii.Error):
            decode_base64_asset(invalid_data)


@pytest.mark.django_db
class TestNormalizeAssets:
    def test_normalize_asset_url_valid_html_type(self):
        asset = baker.make("reporting.ReportAsset", _create_files=True)
        text = f"Some content with link asset://{asset.id} and more content"

        result = normalize_asset_url(text, "html")

        assert f"{asset.file.url}?id={asset.id}" in result
        assert f"asset://{asset.id}" not in result

    def test_normalize_asset_url_valid_pdf_type(self):
        asset = baker.make("reporting.ReportAsset", _create_files=True)
        text = f"Some content with link asset://{asset.id} and more content"

        result = normalize_asset_url(text, "pdf")

        assert f"file://{asset.file.path}" in result
        assert f"asset://{asset.id}" not in result

    def test_normalize_asset_url_invalid_asset(self):
        invalid_id = "11111111-1111-1111-1111-111111111111"  # UUID that's not in the DB
        text = f"Some content with link asset://{invalid_id} and more content"

        result = normalize_asset_url(text, "html")

        # Since the asset doesn't exist, the URL should remain unchanged
        assert f"asset://{invalid_id}" in result

    def test_normalize_asset_url_no_asset(self):
        text = "Some content with no assets"

        result = normalize_asset_url(text, "html")

        # The text remains unchanged
        assert text == result
