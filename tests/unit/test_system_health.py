"""Unit tests for the SystemHealthMonitor evaluation logic."""

import pytest

from labops_ai.config.health_thresholds import (
    HealthThresholds,
)
from labops_ai.system_health import (
    HealthStatus,
    SystemHealthMonitor,
)


TEST_THRESHOLDS = HealthThresholds(
    warning=70.0,
    critical=90.0,
)


@pytest.fixture
def monitor() -> SystemHealthMonitor:
    """
    Create a monitor with deterministic test thresholds.

    The fixture isolates unit tests from the production JSON file.
    Configuration loading is tested separately by integration tests.
    """
    return SystemHealthMonitor(
        thresholds=TEST_THRESHOLDS,
    )


@pytest.mark.unit
class TestSystemHealthMonitor:
    """Verify classification and overall severity behavior."""

    @pytest.mark.parametrize(
        ("metric_value", "expected_status"),
        [
            pytest.param(
                TEST_THRESHOLDS.warning - 0.1,
                HealthStatus.HEALTHY,
                id="below-warning-threshold",
            ),
            pytest.param(
                TEST_THRESHOLDS.warning,
                HealthStatus.WARNING,
                id="at-warning-threshold",
            ),
            pytest.param(
                TEST_THRESHOLDS.critical - 0.1,
                HealthStatus.WARNING,
                id="below-critical-threshold",
            ),
            pytest.param(
                TEST_THRESHOLDS.critical,
                HealthStatus.CRITICAL,
                id="at-critical-threshold",
            ),
            pytest.param(
                TEST_THRESHOLDS.critical + 5.0,
                HealthStatus.CRITICAL,
                id="above-critical-threshold",
            ),
        ],
    )
    def test_evaluate_metric_returns_expected_status(
        self,
        monitor: SystemHealthMonitor,
        metric_value: float,
        expected_status: HealthStatus,
    ) -> None:
        """
        Verify classification around configured threshold boundaries.

        Test values are derived from the injected configuration rather
        than duplicating production constants inside the test logic.
        """
        actual_status = monitor.evaluate_metric(
            metric_value
        )

        assert actual_status is expected_status

    def test_evaluate_system_health_classifies_all_metrics(
        self,
        monitor: SystemHealthMonitor,
    ) -> None:
        """
        Verify that every supplied metric receives a status.

        The returned dictionary must preserve metric names while
        replacing percentage values with HealthStatus values.
        """
        metrics = {
            "cpu_percent": (
                TEST_THRESHOLDS.warning - 0.1
            ),
            "memory_percent": (
                TEST_THRESHOLDS.warning
            ),
            "disk_percent": (
                TEST_THRESHOLDS.critical
            ),
        }

        expected_statuses = {
            "cpu_percent": HealthStatus.HEALTHY,
            "memory_percent": HealthStatus.WARNING,
            "disk_percent": HealthStatus.CRITICAL,
        }

        actual_statuses = (
            monitor.evaluate_system_health(metrics)
        )

        assert actual_statuses == expected_statuses

    @pytest.mark.parametrize(
        ("statuses", "expected_overall_status"),
        [
            pytest.param(
                {
                    "cpu_percent": HealthStatus.HEALTHY,
                    "memory_percent": HealthStatus.HEALTHY,
                    "disk_percent": HealthStatus.HEALTHY,
                },
                HealthStatus.HEALTHY,
                id="all-metrics-healthy",
            ),
            pytest.param(
                {
                    "cpu_percent": HealthStatus.HEALTHY,
                    "memory_percent": HealthStatus.WARNING,
                    "disk_percent": HealthStatus.HEALTHY,
                },
                HealthStatus.WARNING,
                id="one-warning-metric",
            ),
            pytest.param(
                {
                    "cpu_percent": HealthStatus.WARNING,
                    "memory_percent": HealthStatus.CRITICAL,
                    "disk_percent": HealthStatus.HEALTHY,
                },
                HealthStatus.CRITICAL,
                id="one-critical-metric",
            ),
        ],
    )
    def test_get_overall_status_returns_highest_severity(
        self,
        statuses: dict[str, HealthStatus],
        expected_overall_status: HealthStatus,
    ) -> None:
        """
        Verify that overall status represents the highest severity.

        A CRITICAL result has priority over WARNING, and WARNING has
        priority over HEALTHY.
        """
        actual_overall_status = (
            SystemHealthMonitor.get_overall_status(
                statuses
            )
        )

        assert (
            actual_overall_status
            is expected_overall_status
        )