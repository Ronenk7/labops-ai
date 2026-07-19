"""Unit tests for diagnostic bundle configuration."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.diagnostics import (
    DiagnosticBundleCollectionConfig,
    DiagnosticBundleConfig,
    DiagnosticBundleFilesConfig,
    DiagnosticBundleOutputConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_config_cases.json"
)


def build_output() -> DiagnosticBundleOutputConfig:
    """Build valid diagnostic output configuration."""
    return DiagnosticBundleOutputConfig(
        **CASES["valid_output"]
    )


def build_collection() -> DiagnosticBundleCollectionConfig:
    """Build valid diagnostic collection configuration."""
    return DiagnosticBundleCollectionConfig(
        **CASES["valid_collection"]
    )


def build_files() -> DiagnosticBundleFilesConfig:
    """Build valid diagnostic file configuration."""
    return DiagnosticBundleFilesConfig(
        **CASES["valid_files"]
    )


class TestDiagnosticBundleOutputConfig:
    """Test diagnostic archive output settings."""

    def test_accepts_and_normalizes_valid_output(self) -> None:
        config = DiagnosticBundleOutputConfig(
            directory="  runtime/diagnostic_bundles  ",
            archive_prefix="  labops-diagnostic  ",
            timestamp_format="  %Y%m%dT%H%M%SZ  ",
        )

        assert config.directory == (
            "runtime/diagnostic_bundles"
        )
        assert config.archive_prefix == "labops-diagnostic"
        assert config.timestamp_format == "%Y%m%dT%H%M%SZ"

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_prefixes"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_archive_prefix(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_output"])
        values["archive_prefix"] = case["value"]

        with pytest.raises(ValueError):
            DiagnosticBundleOutputConfig(**values)

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_timestamp_formats"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_timestamp_format(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_output"])
        values["timestamp_format"] = case["value"]

        with pytest.raises(ValueError):
            DiagnosticBundleOutputConfig(**values)


class TestDiagnosticBundleCollectionConfig:
    """Test diagnostic artifact inclusion settings."""

    def test_accepts_valid_collection_settings(self) -> None:
        config = build_collection()

        assert config.include_json_report is True
        assert config.include_text_report is True
        assert config.include_incident_snapshot is True

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_boolean_fields"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_non_boolean_flag(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_collection"])
        values[case["field_name"]] = case["value"]

        with pytest.raises(TypeError, match="boolean"):
            DiagnosticBundleCollectionConfig(**values)

    def test_requires_at_least_one_report_format(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="At least one",
        ):
            DiagnosticBundleCollectionConfig(
                include_json_report=False,
                include_text_report=False,
                include_incident_snapshot=True,
            )


class TestDiagnosticBundleFilesConfig:
    """Test artifact names stored inside archives."""

    def test_accepts_valid_file_names(self) -> None:
        config = build_files()

        assert config.manifest_name == "manifest.json"
        assert config.json_report_name == (
            "diagnostic_report.json"
        )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_file_names"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_file_name(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_files"])
        values[case["field_name"]] = case["value"]

        with pytest.raises(ValueError):
            DiagnosticBundleFilesConfig(**values)

    def test_rejects_duplicate_file_names(self) -> None:
        values = dict(CASES["valid_files"])
        values["incident_snapshot_name"] = (
            values["manifest_name"].upper()
        )

        with pytest.raises(
            ValueError,
            match="must be unique",
        ):
            DiagnosticBundleFilesConfig(**values)


class TestDiagnosticBundleConfig:
    """Test the complete diagnostic bundle configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = DiagnosticBundleConfig(
            output=build_output(),
            collection=build_collection(),
            files=build_files(),
        )

        assert config.output.archive_prefix == (
            "labops-diagnostic"
        )
        assert config.files.manifest_name == "manifest.json"

    def test_rejects_invalid_output_model(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticBundleOutputConfig",
        ):
            DiagnosticBundleConfig(
                output=object(),
                collection=build_collection(),
                files=build_files(),
            )