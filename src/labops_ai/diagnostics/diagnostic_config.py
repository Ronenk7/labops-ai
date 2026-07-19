"""Validated configuration models for diagnostic bundles."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


_SAFE_ARCHIVE_PREFIX_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


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
    """Validate a plain file name without directory components."""
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


@dataclass(frozen=True, slots=True)
class DiagnosticBundleOutputConfig:
    """Represent diagnostic archive destination and naming."""

    directory: str
    archive_prefix: str
    timestamp_format: str

    def __post_init__(self) -> None:
        """Validate and normalize output settings."""
        directory = _normalize_non_empty_string(
            "Diagnostic output directory",
            self.directory,
        )
        archive_prefix = _normalize_non_empty_string(
            "Diagnostic archive prefix",
            self.archive_prefix,
        )
        timestamp_format = _normalize_non_empty_string(
            "Diagnostic timestamp format",
            self.timestamp_format,
        )

        if not _SAFE_ARCHIVE_PREFIX_PATTERN.fullmatch(
            archive_prefix
        ):
            raise ValueError(
                "Diagnostic archive prefix must contain only "
                "letters, numbers, dots, underscores, and hyphens."
            )

        if "%" not in timestamp_format:
            raise ValueError(
                "Diagnostic timestamp format must contain "
                "at least one datetime directive."
            )

        sample_timestamp = datetime(
            year=2026,
            month=7,
            day=19,
            hour=10,
            minute=30,
            second=45,
        ).strftime(timestamp_format)

        if not sample_timestamp:
            raise ValueError(
                "Diagnostic timestamp format must produce text."
            )

        if "/" in sample_timestamp or "\\" in sample_timestamp:
            raise ValueError(
                "Diagnostic timestamp format must not produce "
                "path separators."
            )

        object.__setattr__(self, "directory", directory)
        object.__setattr__(
            self,
            "archive_prefix",
            archive_prefix,
        )
        object.__setattr__(
            self,
            "timestamp_format",
            timestamp_format,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticBundleCollectionConfig:
    """Represent which artifacts are included in a bundle."""

    include_json_report: bool
    include_text_report: bool
    include_incident_snapshot: bool

    def __post_init__(self) -> None:
        """Validate all artifact inclusion flags."""
        for field_name in (
            "include_json_report",
            "include_text_report",
            "include_incident_snapshot",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(
                    f"{field_name} must be a boolean."
                )

        if not (
            self.include_json_report
            or self.include_text_report
        ):
            raise ValueError(
                "At least one diagnostic report format "
                "must be enabled."
            )


@dataclass(frozen=True, slots=True)
class DiagnosticBundleFilesConfig:
    """Represent file names stored inside diagnostic archives."""

    manifest_name: str
    json_report_name: str
    text_report_name: str
    incident_snapshot_name: str

    def __post_init__(self) -> None:
        """Validate all configured artifact file names."""
        for field_name in (
            "manifest_name",
            "json_report_name",
            "text_report_name",
            "incident_snapshot_name",
        ):
            normalized_value = _normalize_file_name(
                field_name.replace("_", " ").title(),
                getattr(self, field_name),
            )
            object.__setattr__(
                self,
                field_name,
                normalized_value,
            )

        normalized_names = [
            file_name.casefold()
            for file_name in (
                self.manifest_name,
                self.json_report_name,
                self.text_report_name,
                self.incident_snapshot_name,
            )
        ]

        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError(
                "Diagnostic artifact file names must be unique."
            )


@dataclass(frozen=True, slots=True)
class DiagnosticBundleConfig:
    """Group all diagnostic bundle configuration."""

    output: DiagnosticBundleOutputConfig
    collection: DiagnosticBundleCollectionConfig
    files: DiagnosticBundleFilesConfig

    def __post_init__(self) -> None:
        """Validate the complete diagnostic configuration."""
        if not isinstance(
            self.output,
            DiagnosticBundleOutputConfig,
        ):
            raise TypeError(
                "output must be a "
                "DiagnosticBundleOutputConfig instance."
            )

        if not isinstance(
            self.collection,
            DiagnosticBundleCollectionConfig,
        ):
            raise TypeError(
                "collection must be a "
                "DiagnosticBundleCollectionConfig instance."
            )

        if not isinstance(
            self.files,
            DiagnosticBundleFilesConfig,
        ):
            raise TypeError(
                "files must be a "
                "DiagnosticBundleFilesConfig instance."
            )