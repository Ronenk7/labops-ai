"""Unit tests for psutil-based process checks."""
from __future__ import annotations

from dataclasses import dataclass

import psutil
import pytest

from labops_ai.processes import (
    ProcessCheckStatus,
    ProcessCollectionConfig,
    ProcessCpuThresholds,
    ProcessFailureReason,
    ProcessMemoryThresholds,
    ProcessTargetConfig,
    PsutilProcessChecker,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "processes/process_checker_cases.json"
)


@dataclass(frozen=True)
class FakeMemoryInfo:
    """Represent fake process memory information."""

    rss: int


@dataclass
class FakeProcess:
    """Provide controlled psutil-like process behavior."""

    pid: int
    process_name: str
    cpu_value: float
    memory_bytes: int
    created_at: float
    deny_access: bool = False

    def name(self) -> str:
        return self.process_name

    def cpu_percent(self, interval: float) -> float:
        if self.deny_access:
            raise psutil.AccessDenied(pid=self.pid)

        return self.cpu_value

    def memory_info(self) -> FakeMemoryInfo:
        return FakeMemoryInfo(rss=self.memory_bytes)

    def create_time(self) -> float:
        return self.created_at


def build_target() -> ProcessTargetConfig:
    """Build the configured process target."""
    return ProcessTargetConfig(
        **CASES["target"],
        cpu_thresholds_percent=ProcessCpuThresholds(
            warning=70.0,
            critical=90.0,
        ),
        memory_thresholds_mb=ProcessMemoryThresholds(
            warning=500.0,
            critical=1000.0,
        ),
    )


def build_processes() -> list[FakeProcess]:
    """Build fake processes from external test data."""
    return [
        FakeProcess(
            pid=process["pid"],
            process_name=process["name"],
            cpu_value=process["cpu_percent"],
            memory_bytes=process["memory_bytes"],
            created_at=process["create_time"],
        )
        for process in CASES["processes"]
    ]


class TestPsutilProcessChecker:
    """Test process discovery and metric collection."""

    def test_returns_all_matching_process_instances(self) -> None:
        checker = PsutilProcessChecker(
            collection_config=ProcessCollectionConfig(
                **CASES["collection"]
            ),
            process_iterator=build_processes,
            clock=lambda: CASES["clock_value"],
        )

        result = checker.check(build_target())

        assert result.status is ProcessCheckStatus.RUNNING
        assert result.pids == (101, 102)
        assert result.total_cpu_percent == 20.0
        assert result.total_memory_mb == 150.0
        assert result.longest_runtime_seconds == 100.0

    def test_returns_not_running_result(self) -> None:
        checker = PsutilProcessChecker(
            collection_config=ProcessCollectionConfig(
                **CASES["collection"]
            ),
            process_iterator=lambda: [],
        )

        result = checker.check(build_target())

        assert result.status is ProcessCheckStatus.NOT_RUNNING
        assert result.instances == ()

    def test_returns_access_denied_error(self) -> None:
        denied_process = FakeProcess(
            pid=101,
            process_name="python",
            cpu_value=0.0,
            memory_bytes=0,
            created_at=0.0,
            deny_access=True,
        )
        checker = PsutilProcessChecker(
            collection_config=ProcessCollectionConfig(
                **CASES["collection"]
            ),
            process_iterator=lambda: [denied_process],
        )

        result = checker.check(build_target())

        assert result.status is ProcessCheckStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is ProcessFailureReason.ACCESS_DENIED
        )

    def test_returns_scan_failure(self) -> None:
        def failed_iterator():
            raise OSError("Process table unavailable.")

        checker = PsutilProcessChecker(
            collection_config=ProcessCollectionConfig(
                **CASES["collection"]
            ),
            process_iterator=failed_iterator,
        )

        result = checker.check(build_target())

        assert result.status is ProcessCheckStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is ProcessFailureReason.PROCESS_SCAN_FAILED
        )

    def test_rejects_invalid_target(self) -> None:
        checker = PsutilProcessChecker(
            collection_config=ProcessCollectionConfig(
                **CASES["collection"]
            )
        )

        with pytest.raises(TypeError, match="ProcessTargetConfig"):
            checker.check(object())