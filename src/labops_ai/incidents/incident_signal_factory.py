"""Convert monitoring results into normalized incident signals."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from labops_ai.health_status import HealthStatus
from labops_ai.incidents.incident_models import (
    IncidentSignal,
    IncidentSourceType,
)
from labops_ai.incidents.incident_signal_config import (
    IncidentSignalFactoryConfig,
)
from labops_ai.logs.log_monitor import LogAnalysisSummary
from labops_ai.logs.log_result import LogScanStatus
from labops_ai.network.connectivity_monitor import (
    NetworkConnectivitySummary,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
)
from labops_ai.processes.process_monitor import (
    ProcessMonitoringSummary,
)
from labops_ai.processes.process_result import ProcessCheckStatus
from labops_ai.services.service_monitor import (
    ServiceMonitoringSummary,
)


@dataclass(frozen=True, slots=True)
class IncidentSignalFactory:
    """Create incident signals from all monitoring domains."""

    config: IncidentSignalFactoryConfig

    def __post_init__(self) -> None:
        """Validate the signal formatting configuration."""
        if not isinstance(
            self.config,
            IncidentSignalFactoryConfig,
        ):
            raise TypeError(
                "config must be an "
                "IncidentSignalFactoryConfig instance."
            )

    def from_system(
        self,
        metrics: Mapping[str, float],
        statuses: Mapping[str, HealthStatus],
        metric_labels: Mapping[str, str],
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create one incident signal for each system metric."""
        self._validate_system_mappings(
            metrics=metrics,
            statuses=statuses,
            metric_labels=metric_labels,
        )

        signals: list[IncidentSignal] = []

        for metric_name, label in metric_labels.items():
            value = self._format_number(metrics[metric_name])
            status = statuses[metric_name]

            signals.append(
                IncidentSignal(
                    source_type=IncidentSourceType.SYSTEM,
                    source_id=metric_name,
                    source_label=label,
                    severity=status,
                    description=(
                        self.config.system_description_template.format(
                            label=label,
                            value=value,
                            severity=status.value,
                        )
                    ),
                    observed_at=observed_at,
                )
            )

        return tuple(signals)

    def from_network(
        self,
        summary: NetworkConnectivitySummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create DNS and TCP incident signals."""
        if not isinstance(summary, NetworkConnectivitySummary):
            raise TypeError(
                "summary must be a "
                "NetworkConnectivitySummary instance."
            )

        return (
            self._from_network_result(
                result=summary.dns_result,
                severity=summary.dns_status,
                observed_at=observed_at,
            ),
            self._from_network_result(
                result=summary.tcp_result,
                severity=summary.tcp_status,
                observed_at=observed_at,
            ),
        )

    def from_services(
        self,
        summary: ServiceMonitoringSummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create one signal for each monitored service."""
        if not isinstance(summary, ServiceMonitoringSummary):
            raise TypeError(
                "summary must be a "
                "ServiceMonitoringSummary instance."
            )

        signals: list[IncidentSignal] = []

        for record in summary.records:
            result = record.result

            if (
                result.failure_reason is not None
                or result.error_message is not None
            ):
                details = self._format_failure_details(
                    reason=result.failure_reason,
                    message=result.error_message,
                )
                description = (
                    self.config.service_failure_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        details=details,
                    )
                )
            else:
                description = (
                    self.config.service_state_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        load_state=result.load_state,
                        active_state=result.active_state,
                        sub_state=result.sub_state,
                    )
                )

            signals.append(
                IncidentSignal(
                    source_type=IncidentSourceType.SERVICE,
                    source_id=result.service_name,
                    source_label=result.label,
                    severity=record.health_status,
                    description=description,
                    observed_at=observed_at,
                )
            )

        return tuple(signals)

    def from_processes(
        self,
        summary: ProcessMonitoringSummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create one signal for each monitored process."""
        if not isinstance(summary, ProcessMonitoringSummary):
            raise TypeError(
                "summary must be a "
                "ProcessMonitoringSummary instance."
            )

        signals: list[IncidentSignal] = []

        for record in summary.records:
            result = record.result

            if result.status is ProcessCheckStatus.RUNNING:
                description = (
                    self.config.process_running_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        instances=len(result.instances),
                        cpu_percent=self._format_number(
                            result.total_cpu_percent
                        ),
                        memory_mb=self._format_number(
                            result.total_memory_mb
                        ),
                        longest_runtime_seconds=self._format_number(
                            result.longest_runtime_seconds
                        ),
                    )
                )
            elif result.status is ProcessCheckStatus.NOT_RUNNING:
                description = (
                    self.config.process_not_running_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                    )
                )
            else:
                details = self._format_failure_details(
                    reason=result.failure_reason,
                    message=result.error_message,
                )
                description = (
                    self.config.process_failure_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        details=details,
                    )
                )

            signals.append(
                IncidentSignal(
                    source_type=IncidentSourceType.PROCESS,
                    source_id=result.process_name,
                    source_label=result.label,
                    severity=record.health_status,
                    description=description,
                    observed_at=observed_at,
                )
            )

        return tuple(signals)

    def from_logs(
        self,
        summary: LogAnalysisSummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create one signal for each analyzed log source."""
        if not isinstance(summary, LogAnalysisSummary):
            raise TypeError(
                "summary must be a LogAnalysisSummary instance."
            )

        signals: list[IncidentSignal] = []

        for record in summary.records:
            result = record.result

            if result.status is LogScanStatus.ANALYZED:
                description = (
                    self.config.log_analyzed_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        lines_scanned=result.total_lines_scanned,
                        matches=len(result.matches),
                    )
                )
            else:
                details = self._format_failure_details(
                    reason=result.failure_reason,
                    message=result.error_message,
                )
                description = (
                    self.config.log_failure_description_template.format(
                        label=result.label,
                        status=result.status.value,
                        severity=record.health_status.value,
                        details=details,
                    )
                )

            signals.append(
                IncidentSignal(
                    source_type=IncidentSourceType.LOG,
                    source_id=result.source_id,
                    source_label=result.label,
                    severity=record.health_status,
                    description=description,
                    observed_at=observed_at,
                )
            )

        return tuple(signals)

    def from_all(
        self,
        *,
        system_metrics: Mapping[str, float],
        system_statuses: Mapping[str, HealthStatus],
        system_metric_labels: Mapping[str, str],
        network_summary: NetworkConnectivitySummary,
        service_summary: ServiceMonitoringSummary,
        process_summary: ProcessMonitoringSummary,
        log_summary: LogAnalysisSummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create signals from every monitoring domain."""
        return (
            self.from_system(
                metrics=system_metrics,
                statuses=system_statuses,
                metric_labels=system_metric_labels,
                observed_at=observed_at,
            )
            + self.from_network(
                summary=network_summary,
                observed_at=observed_at,
            )
            + self.from_services(
                summary=service_summary,
                observed_at=observed_at,
            )
            + self.from_processes(
                summary=process_summary,
                observed_at=observed_at,
            )
            + self.from_logs(
                summary=log_summary,
                observed_at=observed_at,
            )
        )

    def _from_network_result(
        self,
        result: ConnectivityCheckResult,
        severity: HealthStatus,
        observed_at: datetime,
    ) -> IncidentSignal:
        """Convert one connectivity result into a signal."""
        label = self.config.network_label_template.format(
            check_type=result.check_type.value,
            target=result.target,
        )

        if result.status is ConnectivityCheckStatus.PASSED:
            if result.latency_ms is None:
                raise ValueError(
                    "A passed network result must contain latency."
                )

            description = (
                self.config.network_success_description_template.format(
                    check_type=result.check_type.value,
                    target=result.target,
                    latency_ms=self._format_number(
                        result.latency_ms
                    ),
                    severity=severity.value,
                )
            )
        else:
            details = self._format_failure_details(
                reason=result.failure_reason,
                message=result.error_message,
            )
            description = (
                self.config.network_failure_description_template.format(
                    check_type=result.check_type.value,
                    target=result.target,
                    severity=severity.value,
                    details=details,
                )
            )

        return IncidentSignal(
            source_type=IncidentSourceType.NETWORK,
            source_id=(
                f"{result.check_type.value.casefold()}:"
                f"{result.target.casefold()}"
            ),
            source_label=label,
            severity=severity,
            description=description,
            observed_at=observed_at,
        )

    def _format_number(self, value: object) -> str:
        """Format one finite numeric value externally."""
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                "Incident signal metric must be numeric."
            )

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(
                "Incident signal metric must be finite."
            )

        return (
            f"{normalized_value:.{self.config.decimal_places}f}"
        )

    def _format_failure_details(
            self,
            reason: Any,
            message: str | None,
    ) -> str:
        """Format normalized failure details without duplicate punctuation."""
        if reason is None:
            raise ValueError(
                "A failed monitoring result must contain "
                "a failure reason."
            )

        reason_value = getattr(reason, "value", None)

        if not isinstance(reason_value, str) or not reason_value:
            raise TypeError(
                "Failure reason must provide a string value."
            )

        if message is None:
            return self.config.failure_reason_template.format(
                reason=reason_value
            )

        normalized_message = message.strip()

        if normalized_message.endswith("."):
            normalized_message = normalized_message[:-1]

        return self.config.failure_with_message_template.format(
            reason=reason_value,
            message=normalized_message,
        )

    @staticmethod
    def _validate_system_mappings(
        metrics: Mapping[str, float],
        statuses: Mapping[str, HealthStatus],
        metric_labels: Mapping[str, str],
    ) -> None:
        """Validate system metric, status, and label consistency."""
        for field_name, value in (
            ("metrics", metrics),
            ("statuses", statuses),
            ("metric_labels", metric_labels),
        ):
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"{field_name} must be a mapping."
                )

        if not metrics:
            raise ValueError(
                "System metric mappings must not be empty."
            )

        metric_names = set(metrics)

        if metric_names != set(statuses):
            raise ValueError(
                "System metrics and statuses must contain "
                "the same keys."
            )

        if metric_names != set(metric_labels):
            raise ValueError(
                "System metrics and labels must contain "
                "the same keys."
            )

        for metric_name, status in statuses.items():
            if not isinstance(metric_name, str):
                raise TypeError(
                    "System metric names must be strings."
                )

            if not metric_name.strip():
                raise ValueError(
                    "System metric names must not be empty."
                )

            if not isinstance(status, HealthStatus):
                raise TypeError(
                    "Every system status must be "
                    "a HealthStatus instance."
                )

        for label in metric_labels.values():
            if not isinstance(label, str):
                raise TypeError(
                    "System metric labels must be strings."
                )

            if not label.strip():
                raise ValueError(
                    "System metric labels must not be empty."
                )