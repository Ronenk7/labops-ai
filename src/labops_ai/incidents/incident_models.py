"""Structured domain models for incident management."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from labops_ai.health_status import HealthStatus


class IncidentSourceType(StrEnum):
    """Define the monitoring domains that can create incidents."""

    SYSTEM = "SYSTEM"
    NETWORK = "NETWORK"
    SERVICE = "SERVICE"
    PROCESS = "PROCESS"
    LOG = "LOG"


class IncidentStatus(StrEnum):
    """Define the lifecycle states of an incident."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class IncidentActionType(StrEnum):
    """Define actions produced while processing a signal."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    RESOLVED = "RESOLVED"
    UNCHANGED = "UNCHANGED"


def _normalize_required_string(
    field_name: str,
    value: object,
) -> str:
    """Validate and normalize a required string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


def _normalize_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and convert a timezone-aware datetime to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must contain timezone information."
        )

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class IncidentSignal:
    """Represent one health observation sent to incident management."""

    source_type: IncidentSourceType
    source_id: str
    source_label: str
    severity: HealthStatus
    description: str
    observed_at: datetime

    def __post_init__(self) -> None:
        """Validate and normalize the incident signal."""
        if not isinstance(self.source_type, IncidentSourceType):
            raise TypeError(
                "source_type must be an IncidentSourceType instance."
            )

        if not isinstance(self.severity, HealthStatus):
            raise TypeError(
                "severity must be a HealthStatus instance."
            )

        source_id = _normalize_required_string(
            "Incident source ID",
            self.source_id,
        )
        source_label = _normalize_required_string(
            "Incident source label",
            self.source_label,
        )
        description = _normalize_required_string(
            "Incident description",
            self.description,
        )
        observed_at = _normalize_aware_datetime(
            "Incident observation time",
            self.observed_at,
        )

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "observed_at", observed_at)

    @property
    def incident_key(self) -> str:
        """Return the stable key used to correlate incidents."""
        return f"{self.source_type.value}:{self.source_id.casefold()}"


@dataclass(frozen=True, slots=True)
class IncidentRecord:
    """Represent one persisted incident and its lifecycle."""

    incident_id: str
    source_type: IncidentSourceType
    source_id: str
    source_label: str
    severity: HealthStatus
    status: IncidentStatus
    description: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the complete incident record."""
        if not isinstance(self.source_type, IncidentSourceType):
            raise TypeError(
                "source_type must be an IncidentSourceType instance."
            )

        if not isinstance(self.severity, HealthStatus):
            raise TypeError(
                "severity must be a HealthStatus instance."
            )

        if self.severity not in {
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        }:
            raise ValueError(
                "Incident severity must be WARNING or CRITICAL."
            )

        if not isinstance(self.status, IncidentStatus):
            raise TypeError(
                "status must be an IncidentStatus instance."
            )

        incident_id = _normalize_required_string(
            "Incident ID",
            self.incident_id,
        )
        source_id = _normalize_required_string(
            "Incident source ID",
            self.source_id,
        )
        source_label = _normalize_required_string(
            "Incident source label",
            self.source_label,
        )
        description = _normalize_required_string(
            "Incident description",
            self.description,
        )
        first_seen_at = _normalize_aware_datetime(
            "Incident first seen time",
            self.first_seen_at,
        )
        last_seen_at = _normalize_aware_datetime(
            "Incident last seen time",
            self.last_seen_at,
        )

        if isinstance(self.occurrence_count, bool) or not isinstance(
            self.occurrence_count,
            int,
        ):
            raise TypeError(
                "Incident occurrence count must be an integer."
            )

        if self.occurrence_count <= 0:
            raise ValueError(
                "Incident occurrence count must be greater than zero."
            )

        if last_seen_at < first_seen_at:
            raise ValueError(
                "Incident last seen time must not be earlier "
                "than first seen time."
            )

        resolved_at = None

        if self.resolved_at is not None:
            resolved_at = _normalize_aware_datetime(
                "Incident resolution time",
                self.resolved_at,
            )

        if self.status is IncidentStatus.RESOLVED:
            if resolved_at is None:
                raise ValueError(
                    "A resolved incident must contain "
                    "a resolution time."
                )

            if resolved_at < last_seen_at:
                raise ValueError(
                    "Incident resolution time must not be earlier "
                    "than last seen time."
                )
        elif resolved_at is not None:
            raise ValueError(
                "An active incident cannot contain "
                "a resolution time."
            )

        object.__setattr__(self, "incident_id", incident_id)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "first_seen_at", first_seen_at)
        object.__setattr__(self, "last_seen_at", last_seen_at)
        object.__setattr__(self, "resolved_at", resolved_at)

    @property
    def incident_key(self) -> str:
        """Return the stable key used to correlate incidents."""
        return f"{self.source_type.value}:{self.source_id.casefold()}"

    @property
    def is_active(self) -> bool:
        """Return whether the incident remains active."""
        return self.status in {
            IncidentStatus.OPEN,
            IncidentStatus.ACKNOWLEDGED,
        }


@dataclass(frozen=True, slots=True)
class IncidentActionResult:
    """Represent the result of processing one health signal."""

    action_type: IncidentActionType
    signal: IncidentSignal
    incident: IncidentRecord | None = None

    def __post_init__(self) -> None:
        """Validate action and incident consistency."""
        if not isinstance(self.action_type, IncidentActionType):
            raise TypeError(
                "action_type must be an IncidentActionType instance."
            )

        if not isinstance(self.signal, IncidentSignal):
            raise TypeError(
                "signal must be an IncidentSignal instance."
            )

        if self.incident is not None and not isinstance(
            self.incident,
            IncidentRecord,
        ):
            raise TypeError(
                "incident must be an IncidentRecord instance or None."
            )

        if self.action_type is IncidentActionType.UNCHANGED:
            self._validate_source_consistency()
            return

        if self.incident is None:
            raise ValueError(
                "A changed incident action must contain "
                "an incident record."
            )

        self._validate_source_consistency()

        if self.action_type is IncidentActionType.RESOLVED:
            if self.incident.status is not IncidentStatus.RESOLVED:
                raise ValueError(
                    "A RESOLVED action must contain "
                    "a resolved incident."
                )
            return

        if not self.incident.is_active:
            raise ValueError(
                "A CREATED or UPDATED action must contain "
                "an active incident."
            )

    def _validate_source_consistency(self) -> None:
        """Ensure an attached incident belongs to the signal source."""
        if self.incident is None:
            return

        if self.incident.incident_key != self.signal.incident_key:
            raise ValueError(
                "Incident action source does not match "
                "the supplied signal."
            )