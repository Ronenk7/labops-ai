"""Validated configuration models for system health monitoring."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType


SUPPORTED_SYSTEM_METRICS = frozenset({"cpu_percent", "memory_percent", "disk_percent"})


def _normalize_non_empty_string(field_name: str, value: object) -> str:
    """Validate and normalize a required string configuration value."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


def _normalize_positive_number(field_name: str, value: object) -> float:
    """Validate and normalize a positive finite numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a numeric value.")

    normalized_value = float(value)

    if not isfinite(normalized_value):
        raise ValueError(f"{field_name} must be a finite value.")

    if normalized_value <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return normalized_value


@dataclass(frozen=True, slots=True)
class HealthThresholds:
    """Represent validated warning and critical percentage thresholds."""

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """Validate and normalize percentage threshold values."""
        normalized_warning = self._normalize_percentage("Warning", self.warning)
        normalized_critical = self._normalize_percentage("Critical", self.critical)

        if normalized_warning >= normalized_critical:
            raise ValueError("Warning threshold must be lower than critical threshold.")

        object.__setattr__(self, "warning", normalized_warning)
        object.__setattr__(self, "critical", normalized_critical)

    @staticmethod
    def _normalize_percentage(field_name: str, value: object) -> float:
        """Validate and normalize one finite percentage value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} threshold must be a numeric value.")

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(f"{field_name} threshold must be a finite value.")

        if not 0.0 <= normalized_value <= 100.0:
            raise ValueError(f"{field_name} threshold must be between 0 and 100.")

        return normalized_value


@dataclass(frozen=True, slots=True)
class SystemHealthCollectionConfig:
    """Represent system metric collection settings."""

    cpu_sample_interval_seconds: float
    disk_mount_point: str

    def __post_init__(self) -> None:
        """Validate and normalize metric collection settings."""
        normalized_interval = _normalize_positive_number(
            "CPU sample interval", self.cpu_sample_interval_seconds
        )
        normalized_mount_point = _normalize_non_empty_string(
            "Disk mount point", self.disk_mount_point
        )

        object.__setattr__(self, "cpu_sample_interval_seconds", normalized_interval)
        object.__setattr__(self, "disk_mount_point", normalized_mount_point)


@dataclass(frozen=True, slots=True)
class SystemHealthReportConfig:
    """Represent externally configured system health report text."""

    title: str
    separator: str
    overall_label: str
    metric_labels: Mapping[str, str]

    def __post_init__(self) -> None:
        """Validate and normalize report labels."""
        normalized_title = _normalize_non_empty_string("Report title", self.title)
        normalized_separator = _normalize_non_empty_string("Report separator", self.separator)
        normalized_overall_label = _normalize_non_empty_string(
            "Overall status label", self.overall_label
        )

        if not isinstance(self.metric_labels, Mapping):
            raise TypeError("Metric labels must be a mapping.")

        normalized_metric_labels: dict[str, str] = {}

        for metric_name, metric_label in self.metric_labels.items():
            normalized_name = _normalize_non_empty_string("Metric name", metric_name)
            normalized_label = _normalize_non_empty_string("Metric label", metric_label)
            normalized_metric_labels[normalized_name] = normalized_label

        if not normalized_metric_labels:
            raise ValueError("Metric labels must not be empty.")

        object.__setattr__(self, "title", normalized_title)
        object.__setattr__(self, "separator", normalized_separator)
        object.__setattr__(self, "overall_label", normalized_overall_label)
        object.__setattr__(self, "metric_labels", MappingProxyType(normalized_metric_labels))


@dataclass(frozen=True, slots=True)
class SystemHealthConfig:
    """Group all configuration required by the system health monitor."""

    collection: SystemHealthCollectionConfig
    metric_thresholds: Mapping[str, HealthThresholds]
    report: SystemHealthReportConfig

    def __post_init__(self) -> None:
        """Validate complete system health configuration consistency."""
        if not isinstance(self.collection, SystemHealthCollectionConfig):
            raise TypeError("collection must be a SystemHealthCollectionConfig instance.")

        if not isinstance(self.metric_thresholds, Mapping):
            raise TypeError("metric_thresholds must be a mapping.")

        if not isinstance(self.report, SystemHealthReportConfig):
            raise TypeError("report must be a SystemHealthReportConfig instance.")

        normalized_thresholds: dict[str, HealthThresholds] = {}

        for metric_name, thresholds in self.metric_thresholds.items():
            normalized_name = _normalize_non_empty_string("Metric name", metric_name)

            if not isinstance(thresholds, HealthThresholds):
                raise TypeError(
                    f"Thresholds for '{normalized_name}' must be a HealthThresholds instance."
                )

            normalized_thresholds[normalized_name] = thresholds

        threshold_names = set(normalized_thresholds)
        report_metric_names = set(self.report.metric_labels)

        if threshold_names != SUPPORTED_SYSTEM_METRICS:
            raise ValueError(
                "System health thresholds must define every supported metric exactly once."
            )

        if report_metric_names != SUPPORTED_SYSTEM_METRICS:
            raise ValueError(
                "System health report labels must define every supported metric exactly once."
            )

        object.__setattr__(
            self,
            "metric_thresholds",
            MappingProxyType(normalized_thresholds),
        )