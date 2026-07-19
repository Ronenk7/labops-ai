"""Validated configuration models for log analysis."""
from __future__ import annotations

import re
from dataclasses import dataclass

from labops_ai.health_status import HealthStatus


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


def _normalize_positive_integer(
    field_name: str,
    value: object,
) -> int:
    """Validate and normalize a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return value


@dataclass(frozen=True, slots=True)
class LogCollectionConfig:
    """Represent settings used while reading log files."""

    encoding: str
    max_lines_per_source: int

    def __post_init__(self) -> None:
        """Validate log collection settings."""
        encoding = _normalize_non_empty_string(
            "Log encoding",
            self.encoding,
        )
        max_lines = _normalize_positive_integer(
            "Maximum lines per source",
            self.max_lines_per_source,
        )

        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(
            self,
            "max_lines_per_source",
            max_lines,
        )


@dataclass(frozen=True, slots=True)
class LogSourceConfig:
    """Represent one configured log source."""

    source_id: str
    label: str
    path: str
    required: bool

    def __post_init__(self) -> None:
        """Validate and normalize the log source."""
        source_id = _normalize_non_empty_string(
            "Log source ID",
            self.source_id,
        )
        label = _normalize_non_empty_string(
            "Log source label",
            self.label,
        )
        path = _normalize_non_empty_string(
            "Log source path",
            self.path,
        )

        if any(character.isspace() for character in source_id):
            raise ValueError(
                "Log source ID must not contain whitespace."
            )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "path", path)


@dataclass(frozen=True, slots=True)
class LogRuleConfig:
    """Represent one externally configured log matching rule."""

    rule_id: str
    label: str
    pattern: str
    severity: HealthStatus
    case_sensitive: bool

    def __post_init__(self) -> None:
        """Validate and normalize the matching rule."""
        rule_id = _normalize_non_empty_string(
            "Log rule ID",
            self.rule_id,
        )
        label = _normalize_non_empty_string(
            "Log rule label",
            self.label,
        )
        pattern = _normalize_non_empty_string(
            "Log rule pattern",
            self.pattern,
        )

        if any(character.isspace() for character in rule_id):
            raise ValueError(
                "Log rule ID must not contain whitespace."
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
                "Log rule severity must be WARNING or CRITICAL."
            )

        if not isinstance(self.case_sensitive, bool):
            raise TypeError(
                "case_sensitive must be a boolean."
            )

        flags = 0 if self.case_sensitive else re.IGNORECASE

        try:
            re.compile(pattern, flags)
        except re.error as error:
            raise ValueError(
                f"Log rule pattern is invalid: {pattern}"
            ) from error

        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "pattern", pattern)


@dataclass(frozen=True, slots=True)
class LogReportConfig:
    """Represent externally configured log report text."""

    title: str
    separator: str
    overall_label: str
    source_label: str
    source_id_label: str
    path_label: str
    required_label: str
    scan_status_label: str
    health_label: str
    lines_scanned_label: str
    matches_label: str
    match_label: str
    rule_label: str
    severity_label: str
    line_number_label: str
    content_label: str
    failure_reason_label: str
    error_message_label: str
    yes_value: str
    no_value: str

    def __post_init__(self) -> None:
        """Validate and normalize all report text."""
        for field_name in self.__dataclass_fields__:
            normalized_value = _normalize_non_empty_string(
                field_name.replace("_", " ").title(),
                getattr(self, field_name),
            )
            object.__setattr__(
                self,
                field_name,
                normalized_value,
            )


@dataclass(frozen=True, slots=True)
class LogAnalyzerConfig:
    """Group all configuration required for log analysis."""

    collection: LogCollectionConfig
    sources: tuple[LogSourceConfig, ...]
    rules: tuple[LogRuleConfig, ...]
    report: LogReportConfig

    def __post_init__(self) -> None:
        """Validate complete log analyzer configuration."""
        if not isinstance(self.collection, LogCollectionConfig):
            raise TypeError(
                "collection must be a LogCollectionConfig instance."
            )

        if not isinstance(self.sources, tuple):
            raise TypeError("sources must be a tuple.")

        if not self.sources:
            raise ValueError(
                "At least one log source must be configured."
            )

        for source in self.sources:
            if not isinstance(source, LogSourceConfig):
                raise TypeError(
                    "Every source must be a LogSourceConfig instance."
                )

        if not isinstance(self.rules, tuple):
            raise TypeError("rules must be a tuple.")

        if not self.rules:
            raise ValueError(
                "At least one log rule must be configured."
            )

        for rule in self.rules:
            if not isinstance(rule, LogRuleConfig):
                raise TypeError(
                    "Every rule must be a LogRuleConfig instance."
                )

        source_ids = [
            source.source_id.casefold()
            for source in self.sources
        ]
        rule_ids = [
            rule.rule_id.casefold()
            for rule in self.rules
        ]

        if len(source_ids) != len(set(source_ids)):
            raise ValueError(
                "Configured log source IDs must be unique."
            )

        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError(
                "Configured log rule IDs must be unique."
            )

        if not isinstance(self.report, LogReportConfig):
            raise TypeError(
                "report must be a LogReportConfig instance."
            )