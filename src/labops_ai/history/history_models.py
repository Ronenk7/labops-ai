"""Models representing persisted monitoring run summaries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from labops_ai.health_status import HealthStatus


def _normalize_non_empty_string(
    field_name: str,
    value: object,
) -> str:
    """Validate and normalize one required string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


def _normalize_positive_integer(
    field_name: str,
    value: object,
) -> int:
    """Validate one positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return value


def _normalize_non_negative_integer(
    field_name: str,
    value: object,
) -> int:
    """Validate one non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(
            f"{field_name} must not be negative."
        )

    return value


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


def _normalize_archive_path(value: object) -> str:
    """Validate and normalize a diagnostic ZIP path."""
    normalized_value = _normalize_non_empty_string(
        "Run history archive path",
        value,
    )

    if Path(normalized_value).suffix.casefold() != ".zip":
        raise ValueError(
            "Run history archive path must use a .zip suffix."
        )

    return normalized_value


@dataclass(frozen=True, slots=True)
class RunHistoryEntry:
    """Represent the stored summary of one monitoring run."""

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
    bundle_id: str
    archive_path: str

    def __post_init__(self) -> None:
        """Validate and normalize the complete run entry."""
        run_id = _normalize_positive_integer(
            "Run history ID",
            self.run_id,
        )
        generated_at = _normalize_aware_datetime(
            "Run history generation time",
            self.generated_at,
        )
        host_name = _normalize_non_empty_string(
            "Run history host name",
            self.host_name,
        )
        active_incident_count = (
            _normalize_non_negative_integer(
                "Run history active incident count",
                self.active_incident_count,
            )
        )
        resolved_incident_count = (
            _normalize_non_negative_integer(
                "Run history resolved incident count",
                self.resolved_incident_count,
            )
        )
        bundle_id = _normalize_non_empty_string(
            "Run history bundle ID",
            self.bundle_id,
        )
        archive_path = _normalize_archive_path(
            self.archive_path
        )

        for field_name in (
            "overall_status",
            "system_status",
            "network_status",
            "service_status",
            "process_status",
            "log_status",
        ):
            if not isinstance(
                getattr(self, field_name),
                HealthStatus,
            ):
                raise TypeError(
                    f"{field_name} must be a "
                    "HealthStatus instance."
                )

        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(
            self,
            "generated_at",
            generated_at,
        )
        object.__setattr__(
            self,
            "host_name",
            host_name,
        )
        object.__setattr__(
            self,
            "active_incident_count",
            active_incident_count,
        )
        object.__setattr__(
            self,
            "resolved_incident_count",
            resolved_incident_count,
        )
        object.__setattr__(
            self,
            "bundle_id",
            bundle_id,
        )
        object.__setattr__(
            self,
            "archive_path",
            archive_path,
        )

    @property
    def incident_count(self) -> int:
        """Return the total number of stored incidents."""
        return (
            self.active_incident_count
            + self.resolved_incident_count
        )
