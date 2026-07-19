"""Persist and restore incident management state using JSON."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.health_status import HealthStatus
from labops_ai.incidents.incident_config import (
    IncidentStorageConfig,
)
from labops_ai.incidents.incident_models import (
    IncidentRecord,
    IncidentSourceType,
    IncidentStatus,
)


_INCIDENT_STORAGE_SCHEMA_VERSION = 1


class IncidentStorageError(RuntimeError):
    """Represent an operating-system incident storage failure."""


class IncidentDataError(IncidentStorageError):
    """Represent invalid or unsupported persisted incident data."""


@dataclass(frozen=True, slots=True)
class IncidentStoreState:
    """Represent all persisted incident records and sequencing data."""

    next_sequence: int
    incidents: tuple[IncidentRecord, ...]

    def __post_init__(self) -> None:
        """Validate the complete incident storage state."""
        if isinstance(self.next_sequence, bool) or not isinstance(
            self.next_sequence,
            int,
        ):
            raise TypeError(
                "next_sequence must be an integer."
            )

        if self.next_sequence <= 0:
            raise ValueError(
                "next_sequence must be greater than zero."
            )

        if not isinstance(self.incidents, tuple):
            raise TypeError("incidents must be a tuple.")

        for incident in self.incidents:
            if not isinstance(incident, IncidentRecord):
                raise TypeError(
                    "Every stored incident must be an "
                    "IncidentRecord instance."
                )

        self._validate_unique_incident_ids()
        self._validate_unique_active_sources()

    @property
    def active_incidents(self) -> tuple[IncidentRecord, ...]:
        """Return incidents that remain active."""
        return tuple(
            incident
            for incident in self.incidents
            if incident.is_active
        )

    @property
    def resolved_incidents(self) -> tuple[IncidentRecord, ...]:
        """Return incidents that have been resolved."""
        return tuple(
            incident
            for incident in self.incidents
            if incident.status is IncidentStatus.RESOLVED
        )

    def find_active(
        self,
        source_type: IncidentSourceType,
        source_id: str,
    ) -> IncidentRecord | None:
        """Find the active incident belonging to one source."""
        if not isinstance(source_type, IncidentSourceType):
            raise TypeError(
                "source_type must be an IncidentSourceType instance."
            )

        if not isinstance(source_id, str):
            raise TypeError("source_id must be a string.")

        normalized_source_id = source_id.strip()

        if not normalized_source_id:
            raise ValueError(
                "source_id must not be empty."
            )

        expected_key = (
            f"{source_type.value}:"
            f"{normalized_source_id.casefold()}"
        )

        for incident in self.active_incidents:
            if incident.incident_key == expected_key:
                return incident

        return None

    def _validate_unique_incident_ids(self) -> None:
        """Reject duplicate incident identifiers."""
        incident_ids = [
            incident.incident_id.casefold()
            for incident in self.incidents
        ]

        if len(incident_ids) != len(set(incident_ids)):
            raise ValueError(
                "Stored incident identifiers must be unique."
            )

    def _validate_unique_active_sources(self) -> None:
        """Reject multiple active incidents for the same source."""
        active_keys = [
            incident.incident_key
            for incident in self.incidents
            if incident.is_active
        ]

        if len(active_keys) != len(set(active_keys)):
            raise ValueError(
                "Only one active incident may exist "
                "for each source."
            )


@dataclass(frozen=True, slots=True)
class JsonIncidentStore:
    """Read and atomically write incident state as JSON."""

    config: IncidentStorageConfig

    def __post_init__(self) -> None:
        """Validate the storage configuration dependency."""
        if not isinstance(self.config, IncidentStorageConfig):
            raise TypeError(
                "config must be an IncidentStorageConfig instance."
            )

    @property
    def path(self) -> Path:
        """Return the resolved incident storage path."""
        configured_path = Path(self.config.path).expanduser()

        if configured_path.is_absolute():
            return configured_path

        return PROJECT_ROOT / configured_path

    def load(self) -> IncidentStoreState:
        """Load persisted state or return a new empty state."""
        try:
            raw_content = self.path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        except OSError as error:
            raise IncidentStorageError(
                f"Incident storage could not be read: {self.path}"
            ) from error

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise IncidentDataError(
                "Incident storage contains invalid JSON."
            ) from error

        return self._deserialize_state(payload)

    def save(self, state: IncidentStoreState) -> None:
        """Persist incident state using an atomic file replacement."""
        if not isinstance(state, IncidentStoreState):
            raise TypeError(
                "state must be an IncidentStoreState instance."
            )

        payload = self._serialize_state(state)
        serialized_payload = (
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        temporary_path: Path | None = None

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(
                file_descriptor,
                mode="w",
                encoding="utf-8",
            ) as temporary_file:
                temporary_file.write(serialized_payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(
                temporary_path,
                self.path,
            )
        except OSError as error:
            raise IncidentStorageError(
                f"Incident storage could not be written: {self.path}"
            ) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @classmethod
    def _serialize_state(
        cls,
        state: IncidentStoreState,
    ) -> dict[str, Any]:
        """Convert validated incident state into JSON data."""
        return {
            "schema_version": (
                _INCIDENT_STORAGE_SCHEMA_VERSION
            ),
            "next_sequence": state.next_sequence,
            "incidents": [
                cls._serialize_incident(incident)
                for incident in state.incidents
            ],
        }

    @staticmethod
    def _serialize_incident(
        incident: IncidentRecord,
    ) -> dict[str, Any]:
        """Convert one incident record into JSON data."""
        return {
            "incident_id": incident.incident_id,
            "source_type": incident.source_type.value,
            "source_id": incident.source_id,
            "source_label": incident.source_label,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "description": incident.description,
            "first_seen_at": (
                incident.first_seen_at.isoformat()
            ),
            "last_seen_at": (
                incident.last_seen_at.isoformat()
            ),
            "occurrence_count": incident.occurrence_count,
            "resolved_at": (
                incident.resolved_at.isoformat()
                if incident.resolved_at is not None
                else None
            ),
        }

    @classmethod
    def _deserialize_state(
        cls,
        payload: object,
    ) -> IncidentStoreState:
        """Convert JSON data into validated incident state."""
        if not isinstance(payload, dict):
            raise IncidentDataError(
                "Incident storage root must be a JSON object."
            )

        cls._validate_exact_keys(
            payload,
            {
                "schema_version",
                "next_sequence",
                "incidents",
            },
            "storage root",
        )

        schema_version = payload["schema_version"]

        if isinstance(schema_version, bool) or not isinstance(
            schema_version,
            int,
        ):
            raise IncidentDataError(
                "Incident storage schema version "
                "must be an integer."
            )

        if schema_version != _INCIDENT_STORAGE_SCHEMA_VERSION:
            raise IncidentDataError(
                "Incident storage schema version is unsupported."
            )

        incident_values = payload["incidents"]

        if not isinstance(incident_values, list):
            raise IncidentDataError(
                "Stored incidents must be a JSON array."
            )

        try:
            incidents = tuple(
                cls._deserialize_incident(value)
                for value in incident_values
            )

            return IncidentStoreState(
                next_sequence=payload["next_sequence"],
                incidents=incidents,
            )
        except IncidentDataError:
            raise
        except (TypeError, ValueError, KeyError) as error:
            raise IncidentDataError(
                "Incident storage state is invalid."
            ) from error

    @classmethod
    def _deserialize_incident(
        cls,
        payload: object,
    ) -> IncidentRecord:
        """Convert one stored JSON object into an incident record."""
        if not isinstance(payload, dict):
            raise IncidentDataError(
                "Every stored incident must be a JSON object."
            )

        cls._validate_exact_keys(
            payload,
            {
                "incident_id",
                "source_type",
                "source_id",
                "source_label",
                "severity",
                "status",
                "description",
                "first_seen_at",
                "last_seen_at",
                "occurrence_count",
                "resolved_at",
            },
            "incident record",
        )

        resolved_value = payload["resolved_at"]

        try:
            resolved_at = (
                cls._parse_datetime(resolved_value)
                if resolved_value is not None
                else None
            )

            return IncidentRecord(
                incident_id=payload["incident_id"],
                source_type=IncidentSourceType(
                    payload["source_type"]
                ),
                source_id=payload["source_id"],
                source_label=payload["source_label"],
                severity=HealthStatus(payload["severity"]),
                status=IncidentStatus(payload["status"]),
                description=payload["description"],
                first_seen_at=cls._parse_datetime(
                    payload["first_seen_at"]
                ),
                last_seen_at=cls._parse_datetime(
                    payload["last_seen_at"]
                ),
                occurrence_count=payload["occurrence_count"],
                resolved_at=resolved_at,
            )
        except (TypeError, ValueError) as error:
            raise IncidentDataError(
                "Stored incident record is invalid."
            ) from error

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        """Parse one stored ISO 8601 datetime value."""
        if not isinstance(value, str):
            raise TypeError(
                "Stored incident datetime must be a string."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "Stored incident datetime must not be empty."
            )

        if normalized_value.endswith("Z"):
            normalized_value = (
                f"{normalized_value[:-1]}+00:00"
            )

        return datetime.fromisoformat(normalized_value)

    @staticmethod
    def _validate_exact_keys(
        payload: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported persisted keys."""
        payload_keys = set(payload)
        missing_keys = required_keys - payload_keys
        unexpected_keys = payload_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise IncidentDataError(
                f"Missing required keys in incident "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(
                sorted(unexpected_keys)
            )
            raise IncidentDataError(
                f"Unsupported keys in incident "
                f"{location}: {formatted_keys}."
            )