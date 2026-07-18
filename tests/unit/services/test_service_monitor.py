"""Unit tests for Linux service health monitoring."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.services import (
    ServiceCheckResult,
    ServiceCheckStatus,
    ServiceMonitor,
    ServiceMonitorConfig,
    ServiceReportConfig,
    ServiceTargetConfig,
    SystemctlCommandConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "services/service_monitor_cases.json"
)
REPORT_CASES = load_test_fixture(
    "services/service_config_cases.json"
)


def build_config() -> ServiceMonitorConfig:
    """Build complete monitor configuration."""
    return ServiceMonitorConfig(
        command=SystemctlCommandConfig(
            executable="systemctl",
            timeout_seconds=5.0,
        ),
        services=tuple(
            ServiceTargetConfig(**service)
            for service in CASES["services"]
        ),
        report=ServiceReportConfig(
            **REPORT_CASES["valid_report"]
        ),
    )


def build_result(
    target: ServiceTargetConfig,
    result_case: dict[str, str],
) -> ServiceCheckResult:
    """Build one structured service result."""
    return ServiceCheckResult(
        service_name=target.service_name,
        label=target.label,
        status=ServiceCheckStatus(result_case["status"]),
        load_state=result_case["load_state"],
        active_state=result_case["active_state"],
        sub_state=result_case["sub_state"],
    )


@dataclass
class FakeServiceChecker:
    """Return configured service results in order."""

    result_cases: tuple[dict[str, str], ...]
    call_index: int = 0

    def check(
        self,
        target: ServiceTargetConfig,
    ) -> ServiceCheckResult:
        result_case = self.result_cases[self.call_index]
        self.call_index += 1
        return build_result(target, result_case)


class TestServiceMonitor:
    """Test complete service monitoring evaluation."""

    def test_returns_healthy_summary_for_active_services(
        self,
    ) -> None:
        config = build_config()
        checker = FakeServiceChecker(
            result_cases=(
                CASES["active_result"],
                CASES["active_result"],
            )
        )
        monitor = ServiceMonitor(
            config=config,
            checker=checker,
        )

        summary = monitor.run()

        assert summary.overall_status is HealthStatus.HEALTHY
        assert len(summary.records) == 2

    def test_returns_warning_for_transitioning_service(
        self,
    ) -> None:
        config = build_config()
        checker = FakeServiceChecker(
            result_cases=(
                CASES["active_result"],
                CASES["transitioning_result"],
            )
        )
        monitor = ServiceMonitor(
            config=config,
            checker=checker,
        )

        summary = monitor.run()

        assert summary.overall_status is HealthStatus.WARNING

    def test_returns_critical_for_failed_service(
        self,
    ) -> None:
        config = build_config()
        checker = FakeServiceChecker(
            result_cases=(
                CASES["active_result"],
                CASES["failed_result"],
            )
        )
        monitor = ServiceMonitor(
            config=config,
            checker=checker,
        )

        summary = monitor.run()

        assert summary.overall_status is HealthStatus.CRITICAL

    def test_rejects_invalid_checker_dependency(self) -> None:
        with pytest.raises(
            TypeError,
            match="callable check method",
        ):
            ServiceMonitor(
                config=build_config(),
                checker=object(),
            )