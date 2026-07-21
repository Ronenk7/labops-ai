"""Tests for Host-specific monitoring profiles."""
from __future__ import annotations

from pathlib import Path

import pytest

from labops_ai.config import utils as config_utils
from labops_ai.health_status import HealthStatus
from labops_ai.processes import (
    ProcessCheckStatus,
    ProcessCollectionConfig,
    ProcessCpuThresholds,
    ProcessMemoryThresholds,
    ProcessMonitor,
    ProcessMonitorConfig,
    ProcessMonitorConfigLoader,
    ProcessReportConfig,
    ProcessTargetConfig,
)
from labops_ai.services import (
    ServiceCheckStatus,
    ServiceMonitor,
    ServiceMonitorConfig,
    ServiceMonitorConfigLoader,
    ServiceReportConfig,
    ServiceTargetConfig,
    SystemctlCommandConfig,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

SERVICE_CASES = load_test_fixture(
    "services/service_config_cases.json"
)
PROCESS_CASES = load_test_fixture(
    "processes/process_config_cases.json"
)


class RejectingChecker:
    """Fail when a disabled target is executed."""

    def check(self, target):
        raise AssertionError(
            "Disabled target must not be checked."
        )


def test_resolves_existing_profile_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Prefer a profile-specific file when present."""
    default_path = tmp_path / "service_monitor.json"
    profile_path = (
        tmp_path
        / "profiles"
        / "container"
        / "service_monitor.json"
    )

    default_path.write_text(
        "{}",
        encoding="utf-8",
    )
    profile_path.parent.mkdir(
        parents=True
    )
    profile_path.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        config_utils,
        "CONFIG_DIRECTORY",
        tmp_path,
    )
    monkeypatch.setenv(
        "LABOPS_AI_MONITORING_PROFILE",
        "container",
    )

    assert config_utils._resolve_config_path(
        "service_monitor.json"
    ) == profile_path


def test_profile_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Use the default file without an override."""
    default_path = tmp_path / "log_analyzer.json"
    default_path.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        config_utils,
        "CONFIG_DIRECTORY",
        tmp_path,
    )
    monkeypatch.setenv(
        "LABOPS_AI_MONITORING_PROFILE",
        "container",
    )

    assert config_utils._resolve_config_path(
        "log_analyzer.json"
    ) == default_path


def test_rejects_unsafe_profile_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent profile-directory traversal."""
    monkeypatch.setenv(
        "LABOPS_AI_MONITORING_PROFILE",
        "../container",
    )

    with pytest.raises(
        ValueError,
        match="unsupported characters",
    ):
        config_utils._resolve_config_path(
            "service_monitor.json"
        )


def test_disabled_services_are_not_applicable() -> None:
    """Do not execute systemd checks in a container."""
    config = ServiceMonitorConfig(
        enabled=False,
        command=SystemctlCommandConfig(
            **SERVICE_CASES["valid_command"]
        ),
        services=tuple(
            ServiceTargetConfig(**service)
            for service in (
                SERVICE_CASES["valid_services"]
            )
        ),
        report=ServiceReportConfig(
            **SERVICE_CASES["valid_report"]
        ),
    )

    summary = ServiceMonitor(
        config=config,
        checker=RejectingChecker(),
    ).run()

    assert summary.overall_status is (
        HealthStatus.HEALTHY
    )
    assert all(
        record.result.status
        is ServiceCheckStatus.NOT_APPLICABLE
        for record in summary.records
    )
    assert all(
        record.health_status
        is HealthStatus.HEALTHY
        for record in summary.records
    )


def test_disabled_process_is_not_applicable() -> None:
    """Do not scan a process excluded by the profile."""
    target = ProcessTargetConfig(
        process_name="systemd",
        label="System Manager",
        required=True,
        enabled=False,
        cpu_thresholds_percent=(
            ProcessCpuThresholds(
                **PROCESS_CASES[
                    "valid_cpu_thresholds"
                ]
            )
        ),
        memory_thresholds_mb=(
            ProcessMemoryThresholds(
                **PROCESS_CASES[
                    "valid_memory_thresholds"
                ]
            )
        ),
    )

    config = ProcessMonitorConfig(
        collection=ProcessCollectionConfig(
            **PROCESS_CASES["valid_collection"]
        ),
        processes=(target,),
        report=ProcessReportConfig(
            **PROCESS_CASES["valid_report"]
        ),
    )

    summary = ProcessMonitor(
        config=config,
        checker=RejectingChecker(),
    ).run()

    record = summary.records[0]

    assert summary.overall_status is (
        HealthStatus.HEALTHY
    )
    assert record.result.status is (
        ProcessCheckStatus.NOT_APPLICABLE
    )
    assert record.health_status is (
        HealthStatus.HEALTHY
    )


def test_container_profile_loaders() -> None:
    """Load the real container profile files."""
    service_config = (
        ServiceMonitorConfigLoader(
            "config/profiles/container/"
            "service_monitor.json"
        ).load()
    )
    process_config = (
        ProcessMonitorConfigLoader(
            "config/profiles/container/"
            "process_monitor.json"
        ).load()
    )

    assert service_config.enabled is False

    enabled_by_name = {
        target.process_name: target.enabled
        for target in process_config.processes
    }

    assert enabled_by_name == {
        "systemd": False,
        "python": True,
    }
