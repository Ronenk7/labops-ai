"""Validated response schemas exposed by the LabOps AI API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry


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
