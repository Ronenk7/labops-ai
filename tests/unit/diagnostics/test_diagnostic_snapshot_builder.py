"""Unit tests for diagnostic snapshot construction."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from labops_ai.diagnostics import DiagnosticSnapshotBuilder
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentRecord,
    IncidentSourceType,
    IncidentStatus,
    IncidentStoreState,
)
from labops_ai.logs.log_config import LogSourceConfig
from labops_ai.logs.log_monitor import (
    LogAnalysisSummary,
    LogHealthRecord,
)
from labops_ai.logs.log_result import (
    LogFailureReason,
    LogScanStatus,
    LogSourceResult,
)
from labops_ai.network.connectivity_monitor import (
    NetworkConnectivitySummary,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.processes.process_config import (
    ProcessCpuThresholds,
    ProcessMemoryThresholds,
    ProcessTargetConfig,
)
from labops_ai.processes.process_monitor import (
    ProcessHealthRecord,
    ProcessMonitoringSummary,
)
from labops_ai.processes.process_result import (
    ProcessCheckResult,
    ProcessCheckStatus,
    ProcessInstanceSnapshot,
)
from labops_ai.services.service_monitor import (
    ServiceHealthRecord,
    ServiceMonitoringSummary,
)
from labops_ai.services.service_result import (
    ServiceCheckResult,
    ServiceCheckStatus,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_snapshot_cases.json"
)
GENERATED_AT = datetime.fromisoformat(CASES["generated_at"])


def build_network_summary() -> NetworkConnectivitySummary:
    """Build controlled network diagnostic input."""
    values = CASES["network"]

    return NetworkConnectivitySummary(
        dns_result=ConnectivityCheckResult(
            check_type=ConnectivityCheckType.DNS,
            status=ConnectivityCheckStatus.PASSED,
            target=values["dns_target"],
            latency_ms=values["dns_latency_ms"],
            resolved_address=values["dns_address"],
        ),
        dns_status=HealthStatus.HEALTHY,
        tcp_result=ConnectivityCheckResult(
            check_type=ConnectivityCheckType.TCP,
            status=ConnectivityCheckStatus.FAILED,
            target=values["tcp_target"],
            failure_reason=ConnectivityFailureReason.TIMEOUT,
            error_message=values["tcp_error"],
        ),
        tcp_status=HealthStatus.CRITICAL,
        overall_status=HealthStatus.CRITICAL,
    )


def build_service_summary() -> ServiceMonitoringSummary:
    """Build controlled service diagnostic input."""
    values = CASES["service"]

    result = ServiceCheckResult(
        service_name=values["active_name"],
        label=values["active_label"],
        status=ServiceCheckStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="running",
    )

    return ServiceMonitoringSummary(
        records=(
            ServiceHealthRecord(
                result=result,
                health_status=HealthStatus.HEALTHY,
            ),
        ),
        overall_status=HealthStatus.HEALTHY,
    )


def build_process_summary() -> ProcessMonitoringSummary:
    """Build controlled process diagnostic input."""
    values = CASES["process"]
    target = ProcessTargetConfig(
        process_name=values["running_name"],
        label=values["running_label"],
        required=True,
        cpu_thresholds_percent=ProcessCpuThresholds(
            warning=70,
            critical=90,
        ),
        memory_thresholds_mb=ProcessMemoryThresholds(
            warning=400,
            critical=600,
        ),
    )
    result = ProcessCheckResult(
        process_name=values["running_name"],
        label=values["running_label"],
        required=True,
        status=ProcessCheckStatus.RUNNING,
        instances=(
            ProcessInstanceSnapshot(
                pid=100,
                cpu_percent=75.5,
                memory_mb=450.25,
                runtime_seconds=1000,
            ),
        ),
    )

    return ProcessMonitoringSummary(
        records=(
            ProcessHealthRecord(
                target=target,
                result=result,
                health_status=HealthStatus.WARNING,
            ),
        ),
        overall_status=HealthStatus.WARNING,
    )


def build_log_summary() -> LogAnalysisSummary:
    """Build controlled log diagnostic input."""
    values = CASES["log"]
    source = LogSourceConfig(
        source_id=values["failed_id"],
        label=values["failed_label"],
        path="/var/log/syslog",
        required=False,
    )
    result = LogSourceResult(
        source_id=values["failed_id"],
        label=values["failed_label"],
        path="/var/log/syslog",
        required=False,
        status=LogScanStatus.CHECK_ERROR,
        total_lines_scanned=0,
        failure_reason=LogFailureReason.FILE_NOT_FOUND,
        error_message=values["failed_message"],
    )

    return LogAnalysisSummary(
        records=(
            LogHealthRecord(
                source=source,
                result=result,
                health_status=HealthStatus.WARNING,
            ),
        ),
        overall_status=HealthStatus.WARNING,
    )


def build_incident_state() -> IncidentStoreState:
    """Build controlled incident diagnostic input."""
    incident = IncidentRecord(
        incident_id=CASES["incidents"]["active_id"],
        source_type=IncidentSourceType.SERVICE,
        source_id="example.service",
        source_label="Example Service",
        severity=HealthStatus.CRITICAL,
        status=IncidentStatus.OPEN,
        description="Service failed.",
        first_seen_at=datetime.fromisoformat(
            "2026-07-19T10:00:00+00:00"
        ),
        last_seen_at=datetime.fromisoformat(
            "2026-07-19T10:15:00+00:00"
        ),
        occurrence_count=2,
    )

    return IncidentStoreState(
        next_sequence=2,
        incidents=(incident,),
    )


def build_snapshot(**overrides):
    """Build a snapshot using controlled monitoring data."""
    system = CASES["system"]
    values = {
        "generated_at": GENERATED_AT,
        "host_name": CASES["host_name"],
        "system_metrics": system["metrics"],
        "system_statuses": {
            name: HealthStatus(status)
            for name, status in system["statuses"].items()
        },
        "system_metric_labels": system["labels"],
        "network_summary": build_network_summary(),
        "service_summary": build_service_summary(),
        "process_summary": build_process_summary(),
        "log_summary": build_log_summary(),
        "incident_state": build_incident_state(),
    }
    values.update(overrides)

    return DiagnosticSnapshotBuilder().build(**values)


class TestDiagnosticSnapshotBuilder:
    """Test conversion of monitoring output to snapshots."""

    def test_builds_complete_diagnostic_snapshot(self) -> None:
        snapshot = build_snapshot()

        assert snapshot.host_name == "Kukner7"
        assert snapshot.generated_at == datetime.fromisoformat(
            CASES["expected_generated_at"]
        )
        assert len(snapshot.system_metrics) == 3
        assert len(snapshot.network_checks) == 2
        assert len(snapshot.services) == 1
        assert len(snapshot.processes) == 1
        assert len(snapshot.logs) == 1
        assert len(snapshot.incidents) == 1

    def test_preserves_domain_statuses_and_failure_details(
        self,
    ) -> None:
        snapshot = build_snapshot()

        assert snapshot.system_overall_status is (
            HealthStatus.CRITICAL
        )
        assert snapshot.network_overall_status is (
            HealthStatus.CRITICAL
        )
        assert snapshot.process_overall_status is (
            HealthStatus.WARNING
        )
        assert snapshot.network_checks[1].failure_reason is (
            ConnectivityFailureReason.TIMEOUT
        )
        assert snapshot.logs[0].failure_reason is (
            LogFailureReason.FILE_NOT_FOUND
        )
        assert snapshot.overall_status is HealthStatus.CRITICAL

    def test_preserves_process_metrics(self) -> None:
        snapshot = build_snapshot()
        process = snapshot.processes[0]

        assert process.instance_count == 1
        assert process.pids == (100,)
        assert process.total_cpu_percent == 75.5
        assert process.total_memory_mb == 450.25
        assert process.longest_runtime_seconds == 1000.0

    def test_normalizes_generation_time_to_utc(self) -> None:
        snapshot = build_snapshot()

        assert snapshot.generated_at.tzinfo is timezone.utc
        assert snapshot.generated_at.hour == 10

    def test_rejects_mismatched_system_keys(self) -> None:
        with pytest.raises(ValueError, match="same keys"):
            build_snapshot(
                system_statuses={
                    "cpu_percent": HealthStatus.HEALTHY
                }
            )

    @pytest.mark.parametrize(
        ("field_name", "value", "expected_message"),
        [
            (
                "network_summary",
                object(),
                "NetworkConnectivitySummary",
            ),
            (
                "service_summary",
                object(),
                "ServiceMonitoringSummary",
            ),
            (
                "process_summary",
                object(),
                "ProcessMonitoringSummary",
            ),
            (
                "log_summary",
                object(),
                "LogAnalysisSummary",
            ),
            (
                "incident_state",
                object(),
                "IncidentStoreState",
            ),
        ],
    )
    def test_rejects_invalid_domain_input(
        self,
        field_name: str,
        value: object,
        expected_message: str,
    ) -> None:
        with pytest.raises(TypeError, match=expected_message):
            build_snapshot(**{field_name: value})

    def test_rejects_generation_time_without_timezone(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            build_snapshot(
                generated_at=datetime(2026, 7, 19, 13, 30)
            )