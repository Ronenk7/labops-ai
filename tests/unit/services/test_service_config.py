"""Unit tests for service monitor configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.services import (
    ServiceMonitorConfig,
    ServiceReportConfig,
    ServiceTargetConfig,
    SystemctlCommandConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "services/service_config_cases.json"
)


def build_report() -> ServiceReportConfig:
    """Build valid report configuration from external test data."""
    return ServiceReportConfig(**CASES["valid_report"])


def build_command() -> SystemctlCommandConfig:
    """Build valid command configuration from external test data."""
    return SystemctlCommandConfig(**CASES["valid_command"])


def build_services() -> tuple[ServiceTargetConfig, ...]:
    """Build valid service targets from external test data."""
    return tuple(
        ServiceTargetConfig(**service)
        for service in CASES["valid_services"]
    )


class TestServiceTargetConfig:
    """Test individual service target configuration."""

    def test_accepts_valid_target(self) -> None:
        target = ServiceTargetConfig(**CASES["valid_target"])

        assert target.service_name == "cron.service"
        assert target.label == "Cron Scheduler"

    def test_strips_surrounding_whitespace(self) -> None:
        target = ServiceTargetConfig(
            **CASES["normalized_target"]
        )

        assert target.service_name == "cron.service"
        assert target.label == "Cron Scheduler"

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_service_names"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_service_names(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            ServiceTargetConfig(
                service_name=case["service_name"],
                label=CASES["valid_target"]["label"],
            )


class TestSystemctlCommandConfig:
    """Test systemctl command configuration."""

    def test_accepts_valid_command_configuration(self) -> None:
        command = build_command()

        assert command.executable == "systemctl"
        assert command.timeout_seconds == 5.0

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_timeouts"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_timeout(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            SystemctlCommandConfig(
                executable=CASES["valid_command"]["executable"],
                timeout_seconds=case["value"],
            )


class TestServiceReportConfig:
    """Test service report configuration."""

    def test_accepts_valid_report_configuration(self) -> None:
        report = build_report()

        assert report.title == CASES["valid_report"]["title"]

    def test_report_configuration_is_immutable(self) -> None:
        report = build_report()

        with pytest.raises(
            (AttributeError, TypeError),
        ):
            setattr(report, "title", "Changed")


class TestServiceMonitorConfig:
    """Test complete service monitor configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = ServiceMonitorConfig(
            command=build_command(),
            services=build_services(),
            report=build_report(),
        )

        assert len(config.services) == 2

    def test_rejects_empty_service_collection(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one service",
        ):
            ServiceMonitorConfig(
                command=build_command(),
                services=(),
                report=build_report(),
            )

    def test_rejects_duplicate_service_names(self) -> None:
        service = ServiceTargetConfig(
            **CASES["valid_target"]
        )

        with pytest.raises(
            ValueError,
            match="must be unique",
        ):
            ServiceMonitorConfig(
                command=build_command(),
                services=(service, service),
                report=build_report(),
            )