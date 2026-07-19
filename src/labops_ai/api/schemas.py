"""Validated response schemas exposed by the LabOps AI API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry
from labops_ai.incidents import (
    IncidentRecord,
    IncidentSourceType,
    IncidentStatus,
)


class ApiHealthResponse(BaseModel):
    """Represent API availability and version information."""

    model_config = ConfigDict(frozen=True)

    service: str
    status: HealthStatus
    version: str


class RunHistoryResponse(BaseModel):
    """Represent one monitoring run returned by the API."""

    model_config = ConfigDict(frozen=True)

    run_id: int
    generated_at: datetime
    host_name: str
    overall_status: HealthStatus
    system_status: HealthStatus
    network_status: HealthStatus
    service_status: HealthStatus
    process_status: HealthStatus
    log_status: HealthStatus
    active_incident_count: int
    resolved_incident_count: int
    incident_count: int
    bundle_id: str
    archive_path: str

    @classmethod
    def from_entry(
        cls,
        entry: RunHistoryEntry,
    ) -> "RunHistoryResponse":
        """Convert one persisted history entry."""
        if not isinstance(entry, RunHistoryEntry):
            raise TypeError(
                "entry must be a RunHistoryEntry."
            )

        return cls(
            run_id=entry.run_id,
            generated_at=entry.generated_at,
            host_name=entry.host_name,
            overall_status=entry.overall_status,
            system_status=entry.system_status,
            network_status=entry.network_status,
            service_status=entry.service_status,
            process_status=entry.process_status,
            log_status=entry.log_status,
            active_incident_count=(
                entry.active_incident_count
            ),
            resolved_incident_count=(
                entry.resolved_incident_count
            ),
            incident_count=entry.incident_count,
            bundle_id=entry.bundle_id,
            archive_path=entry.archive_path,
        )


class StatusDistributionResponse(BaseModel):
    """Count recent runs by overall health state."""

    model_config = ConfigDict(frozen=True)

    healthy: int = Field(ge=0)
    warning: int = Field(ge=0)
    critical: int = Field(ge=0)


class ComponentReliabilityResponse(BaseModel):
    """Represent recent healthy percentage per component."""

    model_config = ConfigDict(frozen=True)

    system: float = Field(ge=0, le=100)
    network: float = Field(ge=0, le=100)
    services: float = Field(ge=0, le=100)
    processes: float = Field(ge=0, le=100)
    logs: float = Field(ge=0, le=100)


class DashboardTrendPointResponse(BaseModel):
    """Represent one run in the dashboard trend chart."""

    model_config = ConfigDict(frozen=True)

    run_id: int = Field(ge=1)
    generated_at: datetime
    status: HealthStatus
    active_incidents: int = Field(ge=0)


class DashboardOverviewResponse(BaseModel):
    """Represent calculated dashboard analytics."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    sample_size: int = Field(ge=0)
    health_score: float = Field(ge=0, le=100)
    active_incident_total: int = Field(ge=0)
    current_healthy_streak: int = Field(ge=0)
    hosts: list[str]
    latest_run: RunHistoryResponse | None
    status_distribution: StatusDistributionResponse
    component_reliability: ComponentReliabilityResponse
    trend: list[DashboardTrendPointResponse]

class IncidentResponse(BaseModel):
    """Represent one persisted infrastructure incident."""

    model_config = ConfigDict(frozen=True)

    incident_id: str
    source_type: IncidentSourceType
    source_id: str
    source_label: str
    severity: HealthStatus
    status: IncidentStatus
    description: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int = Field(ge=1)
    resolved_at: datetime | None
    is_active: bool

    @classmethod
    def from_record(
        cls,
        record: IncidentRecord,
    ) -> "IncidentResponse":
        """Convert one domain incident record."""
        if not isinstance(record, IncidentRecord):
            raise TypeError(
                "record must be an IncidentRecord."
            )

        return cls(
            incident_id=record.incident_id,
            source_type=record.source_type,
            source_id=record.source_id,
            source_label=record.source_label,
            severity=record.severity,
            status=record.status,
            description=record.description,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            occurrence_count=record.occurrence_count,
            resolved_at=record.resolved_at,
            is_active=record.is_active,
        )


class IncidentSummaryResponse(BaseModel):
    """Represent aggregated incident lifecycle counts."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    active: int = Field(ge=0)
    open: int = Field(ge=0)
    acknowledged: int = Field(ge=0)
    resolved: int = Field(ge=0)
    warning: int = Field(ge=0)
    critical: int = Field(ge=0)
    source_counts: dict[str, int]


class RunDetailsResponse(BaseModel):
    """Represent one run with its complete archived diagnostics."""

    model_config = ConfigDict(frozen=True)

    run: RunHistoryResponse
    diagnostics: dict[str, Any]
