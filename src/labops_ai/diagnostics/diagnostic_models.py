"""Structured metadata models for diagnostic bundles."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DiagnosticArtifactType(StrEnum):
    """Define artifacts supported inside diagnostic bundles."""

    JSON_REPORT = "JSON_REPORT"
    TEXT_REPORT = "TEXT_REPORT"
    INCIDENT_SNAPSHOT = "INCIDENT_SNAPSHOT"


def _normalize_non_empty_string(
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


def _normalize_file_name(
    field_name: str,
    value: object,
) -> str:
    """Validate a plain file name."""
    normalized_value = _normalize_non_empty_string(
        field_name,
        value,
    )

    if normalized_value in {".", ".."}:
        raise ValueError(
            f"{field_name} must be a regular file name."
        )

    if "/" in normalized_value or "\\" in normalized_value:
        raise ValueError(
            f"{field_name} must not contain path separators."
        )

    return normalized_value


def _normalize_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and convert an aware datetime to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must contain timezone information."
        )

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class DiagnosticArtifactRecord:
    """Represent metadata for one archived diagnostic artifact."""

    artifact_type: DiagnosticArtifactType
    file_name: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        """Validate and normalize artifact metadata."""
        if not isinstance(
            self.artifact_type,
            DiagnosticArtifactType,
        ):
            raise TypeError(
                "artifact_type must be a "
                "DiagnosticArtifactType instance."
            )

        file_name = _normalize_file_name(
            "Diagnostic artifact file name",
            self.file_name,
        )

        if isinstance(self.size_bytes, bool) or not isinstance(
            self.size_bytes,
            int,
        ):
            raise TypeError(
                "Diagnostic artifact size must be an integer."
            )

        if self.size_bytes < 0:
            raise ValueError(
                "Diagnostic artifact size must not be negative."
            )

        sha256 = _normalize_non_empty_string(
            "Diagnostic artifact SHA-256",
            self.sha256,
        ).lower()

        if not _SHA256_PATTERN.fullmatch(sha256):
            raise ValueError(
                "Diagnostic artifact SHA-256 must contain "
                "exactly 64 hexadecimal characters."
            )

        object.__setattr__(self, "file_name", file_name)
        object.__setattr__(self, "sha256", sha256)


@dataclass(frozen=True, slots=True)
class DiagnosticBundleManifest:
    """Represent validated metadata for one diagnostic bundle."""

    schema_version: int
    bundle_id: str
    generated_at: datetime
    host_name: str
    artifacts: tuple[DiagnosticArtifactRecord, ...]

    def __post_init__(self) -> None:
        """Validate and normalize the complete manifest."""
        if isinstance(self.schema_version, bool) or not isinstance(
            self.schema_version,
            int,
        ):
            raise TypeError(
                "Diagnostic manifest schema version "
                "must be an integer."
            )

        if self.schema_version <= 0:
            raise ValueError(
                "Diagnostic manifest schema version "
                "must be greater than zero."
            )

        bundle_id = _normalize_non_empty_string(
            "Diagnostic bundle ID",
            self.bundle_id,
        )
        generated_at = _normalize_aware_datetime(
            "Diagnostic generation time",
            self.generated_at,
        )
        host_name = _normalize_non_empty_string(
            "Diagnostic host name",
            self.host_name,
        )

        if not isinstance(self.artifacts, tuple):
            raise TypeError(
                "Diagnostic artifacts must be a tuple."
            )

        if not self.artifacts:
            raise ValueError(
                "Diagnostic manifest must contain "
                "at least one artifact."
            )

        for artifact in self.artifacts:
            if not isinstance(
                artifact,
                DiagnosticArtifactRecord,
            ):
                raise TypeError(
                    "Every diagnostic artifact must be a "
                    "DiagnosticArtifactRecord instance."
                )

        artifact_names = [
            artifact.file_name.casefold()
            for artifact in self.artifacts
        ]

        if len(artifact_names) != len(set(artifact_names)):
            raise ValueError(
                "Diagnostic artifact names must be unique."
            )

        artifact_types = [
            artifact.artifact_type
            for artifact in self.artifacts
        ]

        if len(artifact_types) != len(set(artifact_types)):
            raise ValueError(
                "Diagnostic artifact types must be unique."
            )

        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(
            self,
            "generated_at",
            generated_at,
        )
        object.__setattr__(self, "host_name", host_name)