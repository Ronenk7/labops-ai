"""Unit tests for Linux process health reports."""
from __future__ import annotations

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.processes import (
    ProcessCheckResult,
    ProcessCheckStatus,
    ProcessCpuThresholds,
    ProcessHealthRecord,
    ProcessInstanceSnapshot,
    ProcessMemoryThresholds,
    ProcessMonitoringSummary,
    ProcessReportConfig,
    ProcessTargetConfig,
    build_process_report,
    print_process_report,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CONFIG_CASES = load_test_fixture(
    "processes/process_config_cases.json"
)
REPORT_CASES = load_test_fixture(
    "processes/process_report_cases.json"
)
REPORT = ProcessReportConfig(
    **CONFIG_CASES["valid_report"]
)


def build_target(
    process_name: str,
    label: str,
    required: bool,
) -> ProcessTargetConfig:
    """Build one report process target."""
    return ProcessTargetConfig(
        process_name=process_name,
        label=label,
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


def build_summary() -> ProcessMonitoringSummary:
    """Build a controlled process monitoring summary."""
    running_target = build_target(
        "python",
        "Python Runtime",
        True,
    )
    missing_target = build_target(
        "missing-worker",
        "Missing Worker",
        False,
    )

    running_result = ProcessCheckResult(
        process_name="python",
        label="Python Runtime",
        required=True,
        status=ProcessCheckStatus.RUNNING,
        instances=(
            ProcessInstanceSnapshot(
                pid=101,
                cpu_percent=12.5,
                memory_mb=100.0,
                runtime_seconds=100.0,
            ),
            ProcessInstanceSnapshot(
                pid=102,
                cpu_percent=7.5,
                memory_mb=50.0,
                runtime_seconds=50.0,
            ),
        ),
    )
    missing_result = ProcessCheckResult(
        process_name="missing-worker",
        label="Missing Worker",
        required=False,
        status=ProcessCheckStatus.NOT_RUNNING,
    )

    return ProcessMonitoringSummary(
        records=(
            ProcessHealthRecord(
                target=running_target,
                result=running_result,
                health_status=HealthStatus.HEALTHY,
            ),
            ProcessHealthRecord(
                target=missing_target,
                result=missing_result,
                health_status=HealthStatus.WARNING,
            ),
        ),
        overall_status=HealthStatus.WARNING,
    )


class TestBuildProcessReport:
    """Test process report construction."""

    def test_builds_complete_process_report(self) -> None:
        actual_report = build_process_report(
            summary=build_summary(),
            report=REPORT,
        )

        assert (
            actual_report
            == REPORT_CASES["expected_report"]
        )

    def test_rejects_invalid_summary(self) -> None:
        with pytest.raises(
            TypeError,
            match="ProcessMonitoringSummary",
        ):
            build_process_report(
                summary=object(),
                report=REPORT,
            )


class TestPrintProcessReport:
    """Test process report printing."""

    def test_prints_complete_process_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        print_process_report(
            summary=build_summary(),
            report=REPORT,
        )

        captured = capsys.readouterr()

        assert (
            captured.out
            == f'{REPORT_CASES["expected_report"]}\n'
        )
        assert captured.err == ""