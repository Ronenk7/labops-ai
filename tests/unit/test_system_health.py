"""Unit tests for system health collection, evaluation, and reporting."""
from typing import Any
from unittest.mock import patch

import pytest

from labops_ai.config.system_health_config import (
    HealthThresholds,
    SystemHealthCollectionConfig,
    SystemHealthConfig,
    SystemHealthReportConfig,
)
from labops_ai.system_health import (
    HealthStatus,
    SystemHealthMonitor,
    print_health_report,
)
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("system_health_monitor_cases.json")


def build_monitor_config() -> SystemHealthConfig:
    """Build a system health configuration from external fixture data."""
    configuration = CASES["config"]

    return SystemHealthConfig(
        collection=SystemHealthCollectionConfig(
            **configuration["collection"]
        ),
        metric_thresholds={
            metric_name: HealthThresholds(**threshold_values)
            for metric_name, threshold_values in configuration["metrics"].items()
        },
        report=SystemHealthReportConfig(**configuration["report"]),
    )


@pytest.fixture
def monitor() -> SystemHealthMonitor:
    """Create a monitor configured entirely from external fixture data."""
    return SystemHealthMonitor(config=build_monitor_config())


@pytest.mark.unit
class TestSystemHealthMonitor:
    """Verify collection, classification, and severity behavior."""

    def test_collect_system_health_uses_external_settings(
        self,
        monitor: SystemHealthMonitor,
    ) -> None:
        """Verify that collection uses the configured interval and mount point."""
        result = CASES["collection_result"]

        with patch(
            "labops_ai.system_health.psutil.cpu_percent",
            return_value=result["cpu_percent"],
        ) as cpu_mock:
            with patch(
                "labops_ai.system_health.psutil.virtual_memory"
            ) as memory_mock:
                with patch(
                    "labops_ai.system_health.psutil.disk_usage"
                ) as disk_mock:
                    memory_mock.return_value.percent = result["memory_percent"]
                    disk_mock.return_value.percent = result["disk_percent"]

                    metrics = monitor.collect_system_health()

        cpu_mock.assert_called_once_with(
            interval=monitor.config.collection.cpu_sample_interval_seconds
        )
        disk_mock.assert_called_once_with(
            monitor.config.collection.disk_mount_point
        )

        assert metrics == result

    @pytest.mark.parametrize(
        "case",
        CASES["metric_status_cases"],
        ids=lambda case: case["id"],
    )
    def test_evaluate_metric_returns_expected_status(
        self,
        monitor: SystemHealthMonitor,
        case: dict[str, Any],
    ) -> None:
        """Verify classification around each metric's external thresholds."""
        actual_status = monitor.evaluate_metric(
            case["metric_name"],
            case["value"],
        )

        assert actual_status is HealthStatus(case["expected"])

    def test_evaluate_system_health_classifies_all_metrics(
        self,
        monitor: SystemHealthMonitor,
    ) -> None:
        """Verify that every supplied metric receives a status."""
        case = CASES["system_health_case"]

        expected = {
            metric_name: HealthStatus(status)
            for metric_name, status in case["expected_statuses"].items()
        }

        assert monitor.evaluate_system_health(case["metrics"]) == expected

    @pytest.mark.parametrize(
        "case",
        CASES["overall_status_cases"],
        ids=lambda case: case["id"],
    )
    def test_get_overall_status_returns_highest_severity(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that overall status represents the highest severity."""
        statuses = {
            metric_name: HealthStatus(status)
            for metric_name, status in case["statuses"].items()
        }

        assert SystemHealthMonitor.get_overall_status(
            statuses
        ) is HealthStatus(case["expected"])

    def test_print_health_report_uses_external_report_text(
        self,
        monitor: SystemHealthMonitor,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify that report text is produced from external configuration."""
        case = CASES["report_case"]

        statuses = {
            metric_name: HealthStatus(status)
            for metric_name, status in case["statuses"].items()
        }

        print_health_report(
            metrics=case["metrics"],
            statuses=statuses,
            overall_status=HealthStatus(case["overall_status"]),
            report=monitor.config.report,
        )

        assert capsys.readouterr().out == case["expected_output"]