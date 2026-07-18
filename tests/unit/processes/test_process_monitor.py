"""Unit tests for Linux process health monitoring."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.processes import (
    ProcessCheckResult,
    ProcessCheckStatus,
    ProcessCollectionConfig,
    ProcessCpuThresholds,
    ProcessInstanceSnapshot,
    ProcessMemoryThresholds,
    ProcessMonitor,
    ProcessMonitorConfig,
    ProcessReportConfig,
    ProcessTargetConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "processes/process_monitor_cases.json"
)
CONFIG_CASES = load_test_fixture(
    "processes/process_config_cases.json"
)


def build_target(
    required: bool = True,
) -> ProcessTargetConfig:
    """Build a controlled process target."""
    return ProcessTargetConfig(
        process_name="python",
        label="Python Runtime",
        required=required,
        cpu_thresholds_percent=ProcessCpuThresholds(
            warning=70.0,
            critical=90.0,
        ),
        memory_thresholds_mb=ProcessMemoryThresholds(
            warning=500.0,
            critical=1000.0,
        ),
    )


def build_config(
    target: ProcessTargetConfig,
) -> ProcessMonitorConfig:
    """Build complete process monitor configuration."""
    return ProcessMonitorConfig(
        collection=ProcessCollectionConfig(
            cpu_sample_interval_seconds=0.05
        ),
        processes=(target,),
        report=ProcessReportConfig(
            **CONFIG_CASES["valid_report"]
        ),
    )


def build_running_result(
    target: ProcessTargetConfig,
    case_name: str,
) -> ProcessCheckResult:
    """Build one running process result."""
    instance = ProcessInstanceSnapshot(
        **CASES[case_name]
    )

    return ProcessCheckResult(
        process_name=target.process_name,
        label=target.label,
        required=target.required,
        status=ProcessCheckStatus.RUNNING,
        instances=(instance,),
    )


@dataclass
class FakeChecker:
    """Return one controlled process result."""

    result: ProcessCheckResult

    def check(
        self,
        target: ProcessTargetConfig,
    ) -> ProcessCheckResult:
        return self.result


class TestProcessMonitor:
    """Test process health evaluation."""

    @pytest.mark.parametrize(
        ("case_name", "expected_status"),
        [
            ("healthy_instance", HealthStatus.HEALTHY),
            ("warning_cpu_instance", HealthStatus.WARNING),
            (
                "warning_memory_instance",
                HealthStatus.WARNING,
            ),
            ("critical_instance", HealthStatus.CRITICAL),
        ],
    )
    def test_evaluates_running_process_metrics(
        self,
        case_name: str,
        expected_status: HealthStatus,
    ) -> None:
        target = build_target()
        result = build_running_result(
            target,
            case_name,
        )
        monitor = ProcessMonitor(
            config=build_config(target),
            checker=FakeChecker(result),
        )

        summary = monitor.run()

        assert summary.overall_status is expected_status

    def test_required_missing_process_is_critical(self) -> None:
        target = build_target(required=True)
        result = ProcessCheckResult(
            process_name=target.process_name,
            label=target.label,
            required=True,
            status=ProcessCheckStatus.NOT_RUNNING,
        )
        monitor = ProcessMonitor(
            config=build_config(target),
            checker=FakeChecker(result),
        )

        summary = monitor.run()

        assert summary.overall_status is HealthStatus.CRITICAL

    def test_optional_missing_process_is_warning(self) -> None:
        target = build_target(required=False)
        result = ProcessCheckResult(
            process_name=target.process_name,
            label=target.label,
            required=False,
            status=ProcessCheckStatus.NOT_RUNNING,
        )
        monitor = ProcessMonitor(
            config=build_config(target),
            checker=FakeChecker(result),
        )

        summary = monitor.run()

        assert summary.overall_status is HealthStatus.WARNING

    def test_rejects_invalid_checker_dependency(self) -> None:
        target = build_target()

        with pytest.raises(
            TypeError,
            match="callable check method",
        ):
            ProcessMonitor(
                config=build_config(target),
                checker=object(),
            )