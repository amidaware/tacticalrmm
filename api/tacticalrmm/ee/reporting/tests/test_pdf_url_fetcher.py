"""Tests for the URL fetcher used by ee.reporting.utils.generate_pdf."""

from types import SimpleNamespace

import pytest

import ee.reporting.utils


class TestReportAssetURLFetcher:
    def test_blocks_file_url_outside_assets_base_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ee.reporting.utils,
            "reporting_settings",
            SimpleNamespace(REPORTING_ASSETS_BASE_PATH=str(tmp_path)),
        )
        fetcher = ee.reporting.utils.ReportAssetURLFetcher()

        with pytest.raises(ValueError):
            fetcher("file:///etc/passwd")

    def test_allows_file_url_inside_assets_base_path(self, monkeypatch, tmp_path):
        asset_file = tmp_path / "asset.png"
        asset_file.write_bytes(b"png-bytes")
        monkeypatch.setattr(
            ee.reporting.utils,
            "reporting_settings",
            SimpleNamespace(REPORTING_ASSETS_BASE_PATH=str(tmp_path)),
        )
        fetcher = ee.reporting.utils.ReportAssetURLFetcher()

        response = fetcher(f"file://{asset_file}")

        assert b"png-bytes" in response.read()

    def test_blocks_file_url_outside_base_path_with_traversal(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ee.reporting.utils,
            "reporting_settings",
            SimpleNamespace(REPORTING_ASSETS_BASE_PATH=str(tmp_path)),
        )
        fetcher = ee.reporting.utils.ReportAssetURLFetcher()

        with pytest.raises(ValueError):
            fetcher(f"file://{tmp_path}/../../etc/passwd")

    def test_blocks_non_http_protocols(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ee.reporting.utils,
            "reporting_settings",
            SimpleNamespace(REPORTING_ASSETS_BASE_PATH=str(tmp_path)),
        )
        fetcher = ee.reporting.utils.ReportAssetURLFetcher()

        with pytest.raises(ValueError):
            fetcher("ftp://example.com/file")
