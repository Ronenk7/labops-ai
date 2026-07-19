"""Read-only incident access for the LabOps AI API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from labops_ai.api.schemas import (
    IncidentResponse,
    IncidentSummaryResponse,
)
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentSourceType,
    IncidentStatus,
    IncidentStoreState,
)


class IncidentStateReader(Protocol):
    """Define incident storage access required by the API."""

    def load(self) -> IncidentStoreState:
        """Load the current persisted incident state."""


@dataclass(frozen=True, slots=True)
class IncidentApiService:
    """Query and aggregate persisted incident records."""

    reader: IncidentStateReader

    def __post_init__(self) -> None:
        """Validate the incident storage dependency."""
        if not callable(
            getattr(self.reader, "load", None)
        ):
            raise TypeError(
                "reader must provide callable load."
            )

    def list_incidents(
        self,
        *,
        limit: int,
        status: IncidentStatus | None,
        severity: HealthStatus | None,
        source_type: IncidentSourceType | None,
        active_only: bool | None,
    ) -> list[IncidentResponse]:
        """Return filtered incidents, newest first."""
        if isinstance(limit, bool) or not isinstance(
            limit,
            int,
        ):
            raise TypeError(
                "Incident limit must be an integer."
            )

        if not 1 <= limit <= 200:
            raise ValueError(
                "Incident limit must be between 1 and 200."
            )

        incidents = self.reader.load().incidents

        filtered = [
            incident
            for incident in incidents
            if (
                status is None
                or incident.status is status
            )
            and (
                severity is None
                or incident.severity is severity
            )
            and (
                source_type is None
                or incident.source_type is source_type
            )
            and (
                active_only is None
                or incident.is_active is active_only
            )
        ]

        filtered.sort(
            key=lambda incident: (
                incident.last_seen_at,
                incident.incident_id,
            ),
            reverse=True,
        )

        return [
            IncidentResponse.from_record(incident)
            for incident in filtered[:limit]
        ]

    def get_by_id(
        self,
        incident_id: str,
    ) -> IncidentResponse | None:
        """Return one incident by identifier."""
        if not isinstance(incident_id, str):
            raise TypeError(
                "incident_id must be a string."
            )

        normalized_id = incident_id.strip()

        if not normalized_id:
            raise ValueError(
                "incident_id must not be empty."
            )

        expected_id = normalized_id.casefold()

        for incident in self.reader.load().incidents:
            if (
                incident.incident_id.casefold()
                == expected_id
            ):
                return IncidentResponse.from_record(
                    incident
                )

        return None

    def get_summary(
        self,
    ) -> IncidentSummaryResponse:
        """Calculate incident lifecycle statistics."""
        incidents = self.reader.load().incidents

        return IncidentSummaryResponse(
            total=len(incidents),
            active=sum(
                incident.is_active
                for incident in incidents
            ),
            open=sum(
                incident.status is IncidentStatus.OPEN
                for incident in incidents
            ),
            acknowledged=sum(
                incident.status
                is IncidentStatus.ACKNOWLEDGED
                for incident in incidents
            ),
            resolved=sum(
                incident.status
                is IncidentStatus.RESOLVED
                for incident in incidents
            ),
            warning=sum(
                incident.severity
                is HealthStatus.WARNING
                for incident in incidents
            ),
            critical=sum(
                incident.severity
                is HealthStatus.CRITICAL
                for incident in incidents
            ),
            source_counts={
                source_type.value: sum(
                    incident.source_type
                    is source_type
                    for incident in incidents
                )
                for source_type in IncidentSourceType
            },
        )
