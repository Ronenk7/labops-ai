"""Unit tests for process monitor configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.processes import (
    ProcessCollectionConfig,
    ProcessCpuThresholds,
    ProcessMemoryThresholds,
    ProcessMonitorConfig,
    ProcessReportConfig,
    ProcessTargetConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "processes/process_config_cases.json"
)


def build_cpu_thresholds() -> ProcessCpuThresholds:
    """Build valid CPU thresholds."""
    return ProcessCpuThresholds(
        **CASES["valid_cpu_thresholds"]
    )


def build_memory_thresholds() -> ProcessMemoryThresholds:
    """Build valid memory thresholds."""
    return ProcessMemoryThresholds(
        **CASES["valid_memory_thresholds"]
    )


def build_target() -> ProcessTargetConfig:
    """Build a valid process target."""
    return ProcessTargetConfig(
        **CASES["valid_target"],
        cpu_thresholds_percent=build_cpu_thresholds(),
        memory_thresholds_mb=build_memory_thresholds(),
    )


def build_report() -> ProcessReportConfig:
    """Build valid process report configuration."""
    return ProcessReportConfig(
        **CASES["valid_report"]
    )


class TestProcessThresholds:
    """Test process resource threshold models."""

    def test_accepts_valid_cpu_thresholds(self) -> None:
        thresholds = build_cpu_thresholds()

        assert thresholds.warning == 70.0
        assert thresholds.critical == 90.0

    def test_rejects_invalid_cpu_threshold_order(self) -> None:
        with pytest.raises(ValueError, match="must be lower"):
            ProcessCpuThresholds(
                warning=90.0,
                critical=70.0,
            )

    def test_accepts_valid_memory_thresholds(self) -> None:
        thresholds = build_memory_thresholds()

        assert thresholds.warning == 500.0
        assert thresholds.critical == 1000.0

    def test_rejects_invalid_memory_threshold_order(self) -> None:
        with pytest.raises(ValueError, match="must be lower"):
            ProcessMemoryThresholds(
                warning=1000.0,
                critical=500.0,
            )


class TestProcessCollectionConfig:
    """Test process metric collection configuration."""

    def test_accepts_valid_collection_settings(self) -> None:
        config = ProcessCollectionConfig(
            **CASES["valid_collection"]
        )

        assert config.cpu_sample_interval_seconds == 0.05

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_intervals"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_intervals(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            ProcessCollectionConfig(
                cpu_sample_interval_seconds=case["value"]
            )


class TestProcessTargetConfig:
    """Test individual process target configuration."""

    def test_accepts_valid_target(self) -> None:
        target = build_target()

        assert target.process_name == "python"
        assert target.required is True

    def test_rejects_non_boolean_required(self) -> None:
        with pytest.raises(TypeError, match="boolean"):
            ProcessTargetConfig(
                process_name="python",
                label="Python Runtime",
                required=1,
                cpu_thresholds_percent=build_cpu_thresholds(),
                memory_thresholds_mb=build_memory_thresholds(),
            )


class TestProcessMonitorConfig:
    """Test complete process monitor configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = ProcessMonitorConfig(
            collection=ProcessCollectionConfig(
                **CASES["valid_collection"]
            ),
            processes=(build_target(),),
            report=build_report(),
        )

        assert len(config.processes) == 1

    def test_rejects_empty_process_collection(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one process",
        ):
            ProcessMonitorConfig(
                collection=ProcessCollectionConfig(
                    **CASES["valid_collection"]
                ),
                processes=(),
                report=build_report(),
            )

    def test_rejects_duplicate_process_names(self) -> None:
        target = build_target()

        with pytest.raises(
            ValueError,
            match="must be unique",
        ):
            ProcessMonitorConfig(
                collection=ProcessCollectionConfig(
                    **CASES["valid_collection"]
                ),
                processes=(target, target),
                report=build_report(),
            )