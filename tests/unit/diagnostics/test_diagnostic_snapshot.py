"""Unit tests for diagnostic snapshot models."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from labops_ai.diagnostics import (
    DiagnosticIncidentRecord,
    DiagnosticLogRecord,
    DiagnosticNetworkCheck,
    DiagnosticProcessRecord,
    DiagnosticServiceRecord,
    DiagnosticSnapshot,
    DiagnosticSystemMetric,
)
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import IncidentSourceType, IncidentStatus
from labops_ai.logs.log_result import LogScanStatus
from labops_ai.network.connectivity_result import (
    ConnectivityCheckStatus,
    ConnectivityCheckType,
)
from labops_ai.processes.process_result import ProcessCheckStatus
from labops_ai.services.service_result import ServiceCheckStatus


pytestmark = pytest.mark.unit


def aware_time() -> datetime:
    """Return one timezone-aware test datetime."""
    return datetime.fromisoformat("2026-07-19T10:30:00+00:00")


def build_system_metric() -> DiagnosticSystemMetric:
    """Build one valid system metric."""
    return DiagnosticSystemMetric(
        metric_name="cpu_percent",
        label="CPU usage",
        value_percent=20.5,
        health_status=HealthStatus.HEALTHY,
    )


def build_network_check() -> DiagnosticNetworkCheck:
    """Build one valid network check."""
    return DiagnosticNetworkCheck(
        check_type=ConnectivityCheckType.DNS,
        target="www.cloudflare.com",
        check_status=ConnectivityCheckStatus.PASSED,
        health_status=HealthStatus.HEALTHY,
        latency_ms=5.5,
        resolved_address="104.16.124.96",
    )


def build_service() -> DiagnosticServiceRecord:
    """Build one valid service record."""
    return DiagnosticServiceRecord(
        service_name="systemd-journald.service",
        label="System Journal",
        check_status=ServiceCheckStatus.ACTIVE,
        health_status=HealthStatus.HEALTHY,
        load_state="loaded",
        active_state="active",
        sub_state="running",
    )


def build_process() -> DiagnosticProcessRecord:
    """Build one valid process record."""
    return DiagnosticProcessRecord(
        process_name="python",
        label="Python Runtime",
        required=True,
        check_status=ProcessCheckStatus.RUNNING,
        health_status=HealthStatus.HEALTHY,
        instance_count=1,
        pids=(100,),
        total_cpu_percent=5.0,
        total_memory_mb=100.0,
        longest_runtime_seconds=500.0,
    )


def build_log() -> DiagnosticLogRecord:
    """Build one valid log record."""
    return DiagnosticLogRecord(
        source_id="application",
        label="Application Log",
        path="logs/application.log",
        required=True,
        scan_status=LogScanStatus.ANALYZED,
        health_status=HealthStatus.HEALTHY,
        total_lines_scanned=10,
        match_count=0,
    )


def build_incident(
    status: IncidentStatus = IncidentStatus.OPEN,
) -> DiagnosticIncidentRecord:
    """Build one valid incident snapshot."""
    resolved_at = (
        aware_time()
        if status is IncidentStatus.RESOLVED
        else None
    )

    return DiagnosticIncidentRecord(
        incident_id="INC-000001",
        source_type=IncidentSourceType.SERVICE,
        source_id="systemd-journald.service",
        source_label="System Journal",
        severity=HealthStatus.CRITICAL,
        status=status,
        description="Service is not running.",
        first_seen_at=datetime.fromisoformat(
            "2026-07-19T10:00:00+00:00"
        ),
        last_seen_at=datetime.fromisoformat(
            "2026-07-19T10:15:00+00:00"
        ),
        occurrence_count=2,
        resolved_at=resolved_at,
    )


def build_snapshot(
    *,
    system_status: HealthStatus = HealthStatus.HEALTHY,
    network_status: HealthStatus = HealthStatus.HEALTHY,
    incidents: tuple[DiagnosticIncidentRecord, ...] = (),
) -> DiagnosticSnapshot:
    """Build one valid complete diagnostic snapshot."""
    return DiagnosticSnapshot(
        generated_at=aware_time(),
        host_name="Kukner7",
        system_metrics=(build_system_metric(),),
        system_overall_status=system_status,
        network_checks=(build_network_check(),),
        network_overall_status=network_status,
        services=(build_service(),),
        service_overall_status=HealthStatus.HEALTHY,
        processes=(build_process(),),
        process_overall_status=HealthStatus.HEALTHY,
        logs=(build_log(),),
        log_overall_status=HealthStatus.HEALTHY,
        incidents=incidents,
    )


class TestDiagnosticSnapshotRecords:
    """Test individual diagnostic snapshot records."""

    def test_accepts_valid_system_metric(self) -> None:
        metric = build_system_metric()

        assert metric.metric_name == "cpu_percent"
        assert metric.value_percent == 20.5

    def test_rejects_negative_system_metric(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            DiagnosticSystemMetric(
                metric_name="cpu_percent",
                label="CPU usage",
                value_percent=-1,
                health_status=HealthStatus.WARNING,
            )

    def test_rejects_passed_network_check_without_latency(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="must contain latency"):
            DiagnosticNetworkCheck(
                check_type=ConnectivityCheckType.DNS,
                target="www.cloudflare.com",
                check_status=ConnectivityCheckStatus.PASSED,
                health_status=HealthStatus.HEALTHY,
            )

    def test_rejects_process_pid_count_mismatch(self) -> None:
        with pytest.raises(ValueError, match="must match"):
            DiagnosticProcessRecord(
                process_name="python",
                label="Python Runtime",
                required=True,
                check_status=ProcessCheckStatus.RUNNING,
                health_status=HealthStatus.HEALTHY,
                instance_count=2,
                pids=(100,),
                total_cpu_percent=5,
                total_memory_mb=100,
                longest_runtime_seconds=500,
            )

    def test_rejects_resolved_incident_without_time(self) -> None:
        with pytest.raises(ValueError, match="resolution time"):
            DiagnosticIncidentRecord(
                incident_id="INC-000001",
                source_type=IncidentSourceType.SERVICE,
                source_id="example.service",
                source_label="Example Service",
                severity=HealthStatus.CRITICAL,
                status=IncidentStatus.RESOLVED,
                description="Service failed.",
                first_seen_at=aware_time(),
                last_seen_at=aware_time(),
                occurrence_count=1,
            )


class TestDiagnosticSnapshot:
    """Test complete diagnostic snapshots."""

    def test_accepts_and_normalizes_complete_snapshot(self) -> None:
        snapshot = build_snapshot()

        assert snapshot.generated_at.tzinfo is timezone.utc
        assert snapshot.host_name == "Kukner7"
        assert snapshot.overall_status is HealthStatus.HEALTHY

    def test_returns_highest_monitoring_severity(self) -> None:
        snapshot = build_snapshot(
            system_status=HealthStatus.WARNING,
            network_status=HealthStatus.CRITICAL,
        )

        assert snapshot.overall_status is HealthStatus.CRITICAL

    def test_counts_active_and_resolved_incidents(self) -> None:
        active = build_incident()
        resolved = build_incident(IncidentStatus.RESOLVED)

        snapshot = build_snapshot(
            incidents=(active, resolved)
        )

        assert snapshot.active_incident_count == 1
        assert snapshot.resolved_incident_count == 1

    def test_rejects_naive_generation_time(self) -> None:
        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            DiagnosticSnapshot(
                generated_at=datetime(2026, 7, 19, 10, 30),
                host_name="Kukner7",
                system_metrics=(build_system_metric(),),
                system_overall_status=HealthStatus.HEALTHY,
                network_checks=(build_network_check(),),
                network_overall_status=HealthStatus.HEALTHY,
                services=(build_service(),),
                service_overall_status=HealthStatus.HEALTHY,
                processes=(build_process(),),
                process_overall_status=HealthStatus.HEALTHY,
                logs=(build_log(),),
                log_overall_status=HealthStatus.HEALTHY,
                incidents=(),
            )

    def test_rejects_empty_required_collection(self) -> None:
        with pytest.raises(
            ValueError,
            match="system_metrics must not be empty",
        ):
            DiagnosticSnapshot(
                generated_at=aware_time(),
                host_name="Kukner7",
                system_metrics=(),
                system_overall_status=HealthStatus.HEALTHY,
                network_checks=(build_network_check(),),
                network_overall_status=HealthStatus.HEALTHY,
                services=(build_service(),),
                service_overall_status=HealthStatus.HEALTHY,
                processes=(build_process(),),
                process_overall_status=HealthStatus.HEALTHY,
                logs=(build_log(),),
                log_overall_status=HealthStatus.HEALTHY,
                incidents=(),
            )