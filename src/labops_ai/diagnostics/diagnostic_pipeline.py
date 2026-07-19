"""Coordinate diagnostic snapshot creation and bundle writing."""
from __future__ import annotations

import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from labops_ai.diagnostics.diagnostic_bundle_writer import (
    DiagnosticBundleWriteResult,
)
from labops_ai.diagnostics.diagnostic_snapshot import (
    DiagnosticSnapshot,
)
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import IncidentStoreState
from labops_ai.logs import LogAnalysisSummary
from labops_ai.network import NetworkConnectivitySummary
from labops_ai.processes import ProcessMonitoringSummary
from labops_ai.services import ServiceMonitoringSummary


class DiagnosticSnapshotBuilderProtocol(Protocol):
    """Define the snapshot builder interface."""

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
        """Build a normalized diagnostic snapshot."""


class DiagnosticBundleWriterProtocol(Protocol):
    """Define the diagnostic bundle writer interface."""

    def write(
        self,
        snapshot: DiagnosticSnapshot,
    ) -> DiagnosticBundleWriteResult:
        """Write a diagnostic snapshot into an archive."""


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _current_host_name() -> str:
    """Return the current operating system host name."""
    return socket.gethostname()


def _normalize_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and normalize a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must contain timezone information."
        )

    return value.astimezone(timezone.utc)


def _normalize_host_name(value: object) -> str:
    """Validate and normalize a host name."""
    if not isinstance(value, str):
        raise TypeError("Diagnostic host name must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            "Diagnostic host name must not be empty."
        )

    return normalized_value


@dataclass(frozen=True, slots=True)
class DiagnosticBundlePipelineResult:
    """Represent the complete result of diagnostic processing."""

    snapshot: DiagnosticSnapshot
    bundle: DiagnosticBundleWriteResult

    def __post_init__(self) -> None:
        """Validate the pipeline result."""
        if not isinstance(self.snapshot, DiagnosticSnapshot):
            raise TypeError(
                "snapshot must be a DiagnosticSnapshot instance."
            )

        if not isinstance(
            self.bundle,
            DiagnosticBundleWriteResult,
        ):
            raise TypeError(
                "bundle must be a "
                "DiagnosticBundleWriteResult instance."
            )


@dataclass(frozen=True, slots=True)
class DiagnosticBundlePipeline:
    """Create one snapshot and write one diagnostic archive."""

    snapshot_builder: DiagnosticSnapshotBuilderProtocol
    bundle_writer: DiagnosticBundleWriterProtocol
    clock: Callable[[], datetime] = _utc_now
    host_name_provider: Callable[[], str] = (
        _current_host_name
    )

    def __post_init__(self) -> None:
        """Validate all injected pipeline dependencies."""
        if not callable(
            getattr(self.snapshot_builder, "build", None)
        ):
            raise TypeError(
                "snapshot_builder must provide a callable "
                "build method."
            )

        if not callable(
            getattr(self.bundle_writer, "write", None)
        ):
            raise TypeError(
                "bundle_writer must provide a callable "
                "write method."
            )

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

        if not callable(self.host_name_provider):
            raise TypeError(
                "host_name_provider must be callable."
            )

    def run(
        self,
        *,
        system_metrics: Mapping[str, float],
        system_statuses: Mapping[str, HealthStatus],
        system_metric_labels: Mapping[str, str],
        network_summary: NetworkConnectivitySummary,
        service_summary: ServiceMonitoringSummary,
        process_summary: ProcessMonitoringSummary,
        log_summary: LogAnalysisSummary,
        incident_state: IncidentStoreState,
    ) -> DiagnosticBundlePipelineResult:
        """Create and persist one complete diagnostic bundle."""
        generated_at = _normalize_aware_datetime(
            "Diagnostic generation time",
            self.clock(),
        )
        host_name = _normalize_host_name(
            self.host_name_provider()
        )

        snapshot = self.snapshot_builder.build(
            generated_at=generated_at,
            host_name=host_name,
            system_metrics=system_metrics,
            system_statuses=system_statuses,
            system_metric_labels=system_metric_labels,
            network_summary=network_summary,
            service_summary=service_summary,
            process_summary=process_summary,
            log_summary=log_summary,
            incident_state=incident_state,
        )

        if not isinstance(snapshot, DiagnosticSnapshot):
            raise TypeError(
                "Diagnostic snapshot builder must return "
                "DiagnosticSnapshot."
            )

        bundle = self.bundle_writer.write(snapshot)

        if not isinstance(
            bundle,
            DiagnosticBundleWriteResult,
        ):
            raise TypeError(
                "Diagnostic bundle writer must return "
                "DiagnosticBundleWriteResult."
            )

        return DiagnosticBundlePipelineResult(
            snapshot=snapshot,
            bundle=bundle,
        )