"""Unit tests for network report configuration."""
from dataclasses import FrozenInstanceError
import pytest
from labops_ai.network.connectivity_config import NetworkReportConfig
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture("network/connectivity_report_config_cases.json")
VALID_REPORT = CASES["valid_report"]


class TestNetworkReportConfig:
    """Test validation of external network report text."""

    def test_accepts_valid_report_configuration(self) -> None:
        report = NetworkReportConfig(**VALID_REPORT)

        assert report.title == VALID_REPORT["title"]
        assert report.latency_unit == VALID_REPORT["latency_unit"]

    def test_strips_surrounding_whitespace(self) -> None:
        values = {field_name: f"  {field_value}  " for field_name, field_value in VALID_REPORT.items()}

        report = NetworkReportConfig(**values)

        for field_name, expected_value in VALID_REPORT.items():
            assert getattr(report, field_name) == expected_value

    def test_rejects_empty_report_text(self) -> None:
        values = {**VALID_REPORT, "title": CASES["empty_title"]}

        with pytest.raises(ValueError, match="Report title must not be empty"):
            NetworkReportConfig(**values)

    def test_rejects_non_string_report_text(self) -> None:
        values = {**VALID_REPORT, "latency_unit": CASES["invalid_latency_unit"],}

        with pytest.raises(TypeError, match="Latency unit must be a string"):
            NetworkReportConfig(**values)

    def test_report_configuration_is_immutable(self) -> None:
        report = NetworkReportConfig(**VALID_REPORT)

        with pytest.raises(FrozenInstanceError):
            setattr(report, "title", "Changed")