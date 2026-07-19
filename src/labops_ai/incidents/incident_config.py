"""Validated configuration models for incident management."""
from __future__ import annotations

import re
from dataclasses import dataclass, fields


_IDENTIFIER_PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


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


@dataclass(frozen=True, slots=True)
class IncidentStorageConfig:
    """Represent persistent incident storage settings."""

    path: str

    def __post_init__(self) -> None:
        """Validate and normalize the storage path."""
        normalized_path = _normalize_non_empty_string(
            "Incident storage path",
            self.path,
        )

        object.__setattr__(self, "path", normalized_path)


@dataclass(frozen=True, slots=True)
class IncidentIdentifierConfig:
    """Represent the format used for generated incident IDs."""

    prefix: str
    separator: str
    sequence_width: int

    def __post_init__(self) -> None:
        """Validate and normalize incident identifier settings."""
        prefix = _normalize_non_empty_string(
            "Incident identifier prefix",
            self.prefix,
        )

        if not _IDENTIFIER_PREFIX_PATTERN.fullmatch(prefix):
            raise ValueError(
                "Incident identifier prefix must contain only "
                "letters and numbers."
            )

        if not isinstance(self.separator, str):
            raise TypeError(
                "Incident identifier separator must be a string."
            )

        if len(self.separator) != 1:
            raise ValueError(
                "Incident identifier separator must contain "
                "exactly one character."
            )

        if self.separator.isspace():
            raise ValueError(
                "Incident identifier separator must not be whitespace."
            )

        if self.separator.isalnum():
            raise ValueError(
                "Incident identifier separator must not be "
                "a letter or number."
            )

        if isinstance(self.sequence_width, bool) or not isinstance(
            self.sequence_width,
            int,
        ):
            raise TypeError(
                "Incident sequence width must be an integer."
            )

        if not 1 <= self.sequence_width <= 12:
            raise ValueError(
                "Incident sequence width must be between 1 and 12."
            )

        object.__setattr__(self, "prefix", prefix.upper())


@dataclass(frozen=True, slots=True)
class IncidentReportConfig:
    """Represent externally configured incident report text."""

    title: str
    separator: str
    actions_label: str
    created_label: str
    updated_label: str
    resolved_actions_label: str
    unchanged_label: str
    active_count_label: str
    resolved_count_label: str
    incident_label: str
    incident_id_label: str
    source_type_label: str
    source_id_label: str
    source_label: str
    severity_label: str
    status_label: str
    description_label: str
    first_seen_label: str
    last_seen_label: str
    occurrences_label: str
    resolved_at_label: str
    no_incidents_message: str

    def __post_init__(self) -> None:
        """Validate and normalize all report text."""
        for field in fields(self):
            normalized_value = _normalize_non_empty_string(
                field.name.replace("_", " ").title(),
                getattr(self, field.name),
            )
            object.__setattr__(
                self,
                field.name,
                normalized_value,
            )


@dataclass(frozen=True, slots=True)
class IncidentManagementConfig:
    """Group all configuration used by incident management."""

    storage: IncidentStorageConfig
    identifier: IncidentIdentifierConfig
    report: IncidentReportConfig

    def __post_init__(self) -> None:
        """Validate the complete incident configuration."""
        if not isinstance(self.storage, IncidentStorageConfig):
            raise TypeError(
                "storage must be an IncidentStorageConfig instance."
            )

        if not isinstance(
            self.identifier,
            IncidentIdentifierConfig,
        ):
            raise TypeError(
                "identifier must be an "
                "IncidentIdentifierConfig instance."
            )

        if not isinstance(self.report, IncidentReportConfig):
            raise TypeError(
                "report must be an IncidentReportConfig instance."
            )