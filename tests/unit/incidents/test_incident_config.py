"""Unit tests for incident management configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.incidents import (
    IncidentIdentifierConfig,
    IncidentManagementConfig,
    IncidentReportConfig,
    IncidentStorageConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_config_cases.json"
)


def build_storage() -> IncidentStorageConfig:
    """Build valid incident storage configuration."""
    return IncidentStorageConfig(
        **CASES["valid_storage"]
    )


def build_identifier() -> IncidentIdentifierConfig:
    """Build valid incident identifier configuration."""
    return IncidentIdentifierConfig(
        **CASES["valid_identifier"]
    )


def build_report() -> IncidentReportConfig:
    """Build valid incident report configuration."""
    return IncidentReportConfig(
        **CASES["valid_report"]
    )


class TestIncidentStorageConfig:
    """Test incident storage configuration."""

    def test_accepts_and_normalizes_valid_path(self) -> None:
        config = IncidentStorageConfig(
            path="  runtime/incidents.json  "
        )

        assert config.path == "runtime/incidents.json"

    def test_rejects_empty_path(self) -> None:
        with pytest.raises(
            ValueError,
            match="must not be empty",
        ):
            IncidentStorageConfig(path="   ")


class TestIncidentIdentifierConfig:
    """Test generated incident identifier settings."""

    def test_accepts_and_normalizes_valid_identifier(self) -> None:
        config = build_identifier()

        assert config.prefix == "INC"
        assert config.separator == "-"
        assert config.sequence_width == 6

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_prefixes"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_prefix(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises(ValueError, match="letters and numbers"):
            IncidentIdentifierConfig(
                prefix=case["value"],
                separator="-",
                sequence_width=6,
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_separators"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_separator(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises(ValueError):
            IncidentIdentifierConfig(
                prefix="INC",
                separator=case["value"],
                sequence_width=6,
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_sequence_widths"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_sequence_width(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            IncidentIdentifierConfig(
                prefix="INC",
                separator="-",
                sequence_width=case["value"],
            )


class TestIncidentReportConfig:
    """Test incident report configuration."""

    def test_accepts_complete_report_configuration(self) -> None:
        report = build_report()

        assert report.title == (
            "LabOps AI - Incident Management"
        )
        assert report.no_incidents_message


class TestIncidentManagementConfig:
    """Test complete incident management configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = IncidentManagementConfig(
            storage=build_storage(),
            identifier=build_identifier(),
            report=build_report(),
        )

        assert config.storage.path == "runtime/incidents.json"
        assert config.identifier.prefix == "INC"

    def test_rejects_invalid_storage_model(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncidentStorageConfig",
        ):
            IncidentManagementConfig(
                storage=object(),
                identifier=build_identifier(),
                report=build_report(),
            )