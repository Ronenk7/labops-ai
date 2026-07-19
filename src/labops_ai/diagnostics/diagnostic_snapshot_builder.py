"""Build normalized diagnostic snapshots from monitoring output."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from math import isfinite

from labops_ai.diagnostics.diagnostic_snapshot import (
    DiagnosticIncidentRecord,
    DiagnosticLogRecord,
    DiagnosticNetworkCheck,
    DiagnosticProcessRecord,
    DiagnosticServiceRecord,
    DiagnosticSnapshot,
    DiagnosticSystemMetric,
)
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import IncidentStoreState
from labops_ai.logs.log_monitor import LogAnalysisSummary
from labops_ai.network.connectivity_monitor import NetworkConnectivitySummary
from labops_ai.processes.process_monitor import ProcessMonitoringSummary
from labops_ai.services.service_monitor import ServiceMonitoringSummary


class DiagnosticSnapshotBuilder:
    """Convert complete monitoring output into one snapshot."""

    def build(
        self,
        *,
        generated_at: datetime,
        host_name: str,
        system_metrics: Mapping[str, float],
        system_statuses: Mapping[str, HealthStatus],
        system_metric_labels: Mapping[str, str],
        network_summary: NetworkConnectivitySummary,
        service_summary: ServiceMonitoringSummary,
        process_summary: ProcessMonitoringSummary,
        log_summary: LogAnalysisSummary,
        incident_state: IncidentStoreState,
    ) -> DiagnosticSnapshot:
        """Build a complete diagnostic snapshot."""
        self._validate_system_data(
            metrics=system_metrics,
            statuses=system_statuses,
            labels=system_metric_labels,
        )

        if not isinstance(network_summary, NetworkConnectivitySummary):
            raise TypeError(
                "network_summary must be a "
                "NetworkConnectivitySummary instance."
            )

        if not isinstance(service_summary, ServiceMonitoringSummary):
            raise TypeError(
                "service_summary must be a "
                "ServiceMonitoringSummary instance."
            )

        if not isinstance(process_summary, ProcessMonitoringSummary):
            raise TypeError(
                "process_summary must be a "
                "ProcessMonitoringSummary instance."
            )

        if not isinstance(log_summary, LogAnalysisSummary):
            raise TypeError(
                "log_summary must be a LogAnalysisSummary instance."
            )

        if not isinstance(incident_state, IncidentStoreState):
            raise TypeError(
                "incident_state must be an IncidentStoreState instance."
            )

        system_records = tuple(
            DiagnosticSystemMetric(
                metric_name=metric_name,
                label=system_metric_labels[metric_name],
                value_percent=system_metrics[metric_name],
                health_status=system_statuses[metric_name],
            )
            for metric_name in system_metric_labels
        )

        network_records = (
            self._build_network_record(
                network_summary.dns_result,
                network_summary.dns_status,
            ),
            self._build_network_record(
                network_summary.tcp_result,
                network_summary.tcp_status,
            ),
        )

        service_records = tuple(
            DiagnosticServiceRecord(
                service_name=record.result.service_name,
                label=record.result.label,
                check_status=record.result.status,
                health_status=record.health_status,
                load_state=record.result.load_state,
                active_state=record.result.active_state,
                sub_state=record.result.sub_state,
                failure_reason=record.result.failure_reason,
                error_message=record.result.error_message,
            )
            for record in service_summary.records
        )

        process_records = tuple(
            DiagnosticProcessRecord(
                process_name=record.result.process_name,
                label=record.result.label,
                required=record.result.required,
                check_status=record.result.status,
                health_status=record.health_status,
                instance_count=len(record.result.instances),
                pids=record.result.pids,
                total_cpu_percent=record.result.total_cpu_percent,
                total_memory_mb=record.result.total_memory_mb,
                longest_runtime_seconds=(
                    record.result.longest_runtime_seconds
                ),
                failure_reason=record.result.failure_reason,
                error_message=record.result.error_message,
            )
            for record in process_summary.records
        )

        log_records = tuple(
            DiagnosticLogRecord(
                source_id=record.result.source_id,
                label=record.result.label,
                path=record.result.path,
                required=record.result.required,
                scan_status=record.result.status,
                health_status=record.health_status,
                total_lines_scanned=record.result.total_lines_scanned,
                match_count=len(record.result.matches),
                failure_reason=record.result.failure_reason,
                error_message=record.result.error_message,
            )
            for record in log_summary.records
        )

        incident_records = tuple(
            DiagnosticIncidentRecord(
                incident_id=incident.incident_id,
                source_type=incident.source_type,
                source_id=incident.source_id,
                source_label=incident.source_label,
                severity=incident.severity,
                status=incident.status,
                description=incident.description,
                first_seen_at=incident.first_seen_at,
                last_seen_at=incident.last_seen_at,
                occurrence_count=incident.occurrence_count,
                resolved_at=incident.resolved_at,
            )
            for incident in incident_state.incidents
        )

        return DiagnosticSnapshot(
            generated_at=generated_at,
            host_name=host_name,
            system_metrics=system_records,
            system_overall_status=self._get_overall_status(
                tuple(system_statuses.values())
            ),
            network_checks=network_records,
            network_overall_status=network_summary.overall_status,
            services=service_records,
            service_overall_status=service_summary.overall_status,
            processes=process_records,
            process_overall_status=process_summary.overall_status,
            logs=log_records,
            log_overall_status=log_summary.overall_status,
            incidents=incident_records,
        )

    @staticmethod
    def _build_network_record(
        result: object,
        health_status: HealthStatus,
    ) -> DiagnosticNetworkCheck:
        """Build one normalized network record."""
        return DiagnosticNetworkCheck(
            check_type=result.check_type,
            target=result.target,
            check_status=result.status,
            health_status=health_status,
            latency_ms=result.latency_ms,
            resolved_address=result.resolved_address,
            failure_reason=result.failure_reason,
            error_message=result.error_message,
        )

    @staticmethod
    def _get_overall_status(
        statuses: tuple[HealthStatus, ...],
    ) -> HealthStatus:
        """Return the highest supplied severity."""
        if not statuses:
            raise ValueError(
                "At least one system health status is required."
            )

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def _validate_system_data(
        *,
        metrics: Mapping[str, float],
        statuses: Mapping[str, HealthStatus],
        labels: Mapping[str, str],
    ) -> None:
        """Validate system metric mapping consistency."""
        for field_name, value in (
            ("system_metrics", metrics),
            ("system_statuses", statuses),
            ("system_metric_labels", labels),
        ):
            if not isinstance(value, Mapping):
                raise TypeError(f"{field_name} must be a mapping.")

        if not metrics:
            raise ValueError("System metrics must not be empty.")

        metric_names = set(metrics)

        if metric_names != set(statuses):
            raise ValueError(
                "System metrics and statuses must contain the same keys."
            )

        if metric_names != set(labels):
            raise ValueError(
                "System metrics and labels must contain the same keys."
            )

        for metric_name, metric_value in metrics.items():
            if not isinstance(metric_name, str) or not metric_name.strip():
                raise ValueError(
                    "System metric names must be populated strings."
                )

            if isinstance(metric_value, bool) or not isinstance(
                metric_value, (int, float)
            ):
                raise TypeError("System metric values must be numeric.")

            if not isfinite(float(metric_value)):
                raise ValueError("System metric values must be finite.")

            if float(metric_value) < 0.0:
                raise ValueError(
                    "System metric values must not be negative."
                )

        for status in statuses.values():
            if not isinstance(status, HealthStatus):
                raise TypeError(
                    "Every system status must be a HealthStatus instance."
                )

        for label in labels.values():
            if not isinstance(label, str) or not label.strip():
                raise ValueError(
                    "System metric labels must be populated strings."
                )