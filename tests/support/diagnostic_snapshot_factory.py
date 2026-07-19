"""Reusable diagnostic snapshot factory for automated tests."""
from __future__ import annotations
from datetime import datetime
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
from labops_ai.incidents import (
    IncidentSourceType,
    IncidentStatus,
)
from labops_ai.logs.log_result import (
    LogFailureReason,
    LogScanStatus,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.processes.process_result import (
    ProcessCheckStatus,
)
from labops_ai.services.service_result import (
    ServiceCheckStatus,
)


def build_test_diagnostic_snapshot() -> DiagnosticSnapshot:
    """Build a complete deterministic diagnostic snapshot."""
    generated_at = datetime.fromisoformat(
        "2026-07-19T10:30:00+00:00"
    )

    return DiagnosticSnapshot(
        generated_at=generated_at,
        host_name="Kukner7",
        system_metrics=(
            DiagnosticSystemMetric(
                metric_name="cpu_percent",
                label="CPU usage",
                value_percent=72.5,
                health_status=HealthStatus.WARNING,
            ),
            DiagnosticSystemMetric(
                metric_name="memory_percent",
                label="Memory usage",
                value_percent=40.25,
                health_status=HealthStatus.HEALTHY,
            ),
        ),
        system_overall_status=HealthStatus.WARNING,
        network_checks=(
            DiagnosticNetworkCheck(
                check_type=ConnectivityCheckType.DNS,
                target="www.cloudflare.com",
                check_status=ConnectivityCheckStatus.PASSED,
                health_status=HealthStatus.HEALTHY,
                latency_ms=6.25,
                resolved_address="104.16.124.96",
            ),
            DiagnosticNetworkCheck(
                check_type=ConnectivityCheckType.TCP,
                target="1.1.1.1:443",
                check_status=ConnectivityCheckStatus.FAILED,
                health_status=HealthStatus.CRITICAL,
                failure_reason=(
                    ConnectivityFailureReason.TIMEOUT
                ),
                error_message="Connection timed out.",
            ),
        ),
        network_overall_status=HealthStatus.CRITICAL,
        services=(
            DiagnosticServiceRecord(
                service_name="systemd-journald.service",
                label="System Journal",
                check_status=ServiceCheckStatus.ACTIVE,
                health_status=HealthStatus.HEALTHY,
                load_state="loaded",
                active_state="active",
                sub_state="running",
            ),
        ),
        service_overall_status=HealthStatus.HEALTHY,
        processes=(
            DiagnosticProcessRecord(
                process_name="python",
                label="Python Runtime",
                required=True,
                check_status=ProcessCheckStatus.RUNNING,
                health_status=HealthStatus.WARNING,
                instance_count=1,
                pids=(100,),
                total_cpu_percent=75.5,
                total_memory_mb=450.25,
                longest_runtime_seconds=1000,
            ),
        ),
        process_overall_status=HealthStatus.WARNING,
        logs=(
            DiagnosticLogRecord(
                source_id="system",
                label="System Log",
                path="/var/log/syslog",
                required=False,
                scan_status=LogScanStatus.CHECK_ERROR,
                health_status=HealthStatus.WARNING,
                total_lines_scanned=0,
                match_count=0,
                failure_reason=(
                    LogFailureReason.FILE_NOT_FOUND
                ),
                error_message="Log file was not found.",
            ),
        ),
        log_overall_status=HealthStatus.WARNING,
        incidents=(
            DiagnosticIncidentRecord(
                incident_id="INC-000001",
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
            ),
            DiagnosticIncidentRecord(
                incident_id="INC-000002",
                source_type=IncidentSourceType.NETWORK,
                source_id="dns:www.cloudflare.com",
                source_label="Cloudflare DNS",
                severity=HealthStatus.WARNING,
                status=IncidentStatus.RESOLVED,
                description="DNS latency was elevated.",
                first_seen_at=datetime.fromisoformat(
                    "2026-07-19T09:00:00+00:00"
                ),
                last_seen_at=datetime.fromisoformat(
                    "2026-07-19T09:10:00+00:00"
                ),
                occurrence_count=3,
                resolved_at=datetime.fromisoformat(
                    "2026-07-19T09:20:00+00:00"
                ),
            ),
        ),
    )