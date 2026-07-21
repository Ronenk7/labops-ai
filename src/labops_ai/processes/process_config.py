"""Validated configuration models for Linux process monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


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


def _normalize_positive_number(
    field_name: str,
    value: object,
) -> float:
    """Validate and normalize a positive finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a numeric value.")

    normalized_value = float(value)

    if not isfinite(normalized_value):
        raise ValueError(f"{field_name} must be a finite value.")

    if normalized_value <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return normalized_value


@dataclass(frozen=True, slots=True)
class ProcessCpuThresholds:
    """Represent warning and critical process CPU thresholds."""

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """Validate CPU percentage thresholds."""
        warning = self._normalize_percentage(
            "CPU warning threshold",
            self.warning,
        )
        critical = self._normalize_percentage(
            "CPU critical threshold",
            self.critical,
        )

        if warning >= critical:
            raise ValueError(
                "CPU warning threshold must be lower than "
                "the critical threshold."
            )

        object.__setattr__(self, "warning", warning)
        object.__setattr__(self, "critical", critical)

    @staticmethod
    def _normalize_percentage(
        field_name: str,
        value: object,
    ) -> float:
        """Validate one finite percentage."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(f"{field_name} must be finite.")

        if not 0.0 <= normalized_value <= 100.0:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

        return normalized_value


@dataclass(frozen=True, slots=True)
class ProcessMemoryThresholds:
    """Represent warning and critical memory thresholds in MB."""

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """Validate memory thresholds."""
        warning = _normalize_positive_number(
            "Memory warning threshold",
            self.warning,
        )
        critical = _normalize_positive_number(
            "Memory critical threshold",
            self.critical,
        )

        if warning >= critical:
            raise ValueError(
                "Memory warning threshold must be lower than "
                "the critical threshold."
            )

        object.__setattr__(self, "warning", warning)
        object.__setattr__(self, "critical", critical)


@dataclass(frozen=True, slots=True)
class ProcessCollectionConfig:
    """Represent process metric collection settings."""

    cpu_sample_interval_seconds: float

    def __post_init__(self) -> None:
        """Validate the process CPU sampling interval."""
        normalized_interval = _normalize_positive_number(
            "Process CPU sample interval",
            self.cpu_sample_interval_seconds,
        )

        object.__setattr__(
            self,
            "cpu_sample_interval_seconds",
            normalized_interval,
        )


@dataclass(frozen=True, slots=True)
class ProcessTargetConfig:
    """Represent one configured process target."""

    process_name: str
    label: str
    required: bool
    cpu_thresholds_percent: ProcessCpuThresholds
    memory_thresholds_mb: ProcessMemoryThresholds
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize the process target."""
        process_name = _normalize_non_empty_string(
            "Process name",
            self.process_name,
        )
        label = _normalize_non_empty_string(
            "Process label",
            self.label,
        )

        if not isinstance(self.enabled, bool):
            raise TypeError(
                "enabled must be a boolean."
            )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        if not isinstance(
            self.cpu_thresholds_percent,
            ProcessCpuThresholds,
        ):
            raise TypeError(
                "cpu_thresholds_percent must be a "
                "ProcessCpuThresholds instance."
            )

        if not isinstance(
            self.memory_thresholds_mb,
            ProcessMemoryThresholds,
        ):
            raise TypeError(
                "memory_thresholds_mb must be a "
                "ProcessMemoryThresholds instance."
            )

        object.__setattr__(self, "process_name", process_name)
        object.__setattr__(self, "label", label)


@dataclass(frozen=True, slots=True)
class ProcessReportConfig:
    """Represent externally configured process report formatting."""

    title: str
    separator: str
    overall_label: str
    process_label: str
    name_label: str
    required_label: str
    check_status_label: str
    health_label: str
    instances_label: str
    pids_label: str
    cpu_label: str
    memory_label: str
    runtime_label: str
    failure_reason_label: str
    error_message_label: str
    yes_value: str
    no_value: str
    cpu_unit: str
    memory_unit: str
    runtime_unit: str
    decimal_places: int

    def __post_init__(self) -> None:
        """Validate all report text and formatting settings."""
        text_fields = (
            "title",
            "separator",
            "overall_label",
            "process_label",
            "name_label",
            "required_label",
            "check_status_label",
            "health_label",
            "instances_label",
            "pids_label",
            "cpu_label",
            "memory_label",
            "runtime_label",
            "failure_reason_label",
            "error_message_label",
            "yes_value",
            "no_value",
            "cpu_unit",
            "memory_unit",
            "runtime_unit",
        )

        for field_name in text_fields:
            normalized_value = _normalize_non_empty_string(
                field_name.replace("_", " ").title(),
                getattr(self, field_name),
            )
            object.__setattr__(
                self,
                field_name,
                normalized_value,
            )

        if isinstance(self.decimal_places, bool) or not isinstance(
            self.decimal_places,
            int,
        ):
            raise TypeError("decimal_places must be an integer.")

        if not 0 <= self.decimal_places <= 6:
            raise ValueError(
                "decimal_places must be between 0 and 6."
            )


@dataclass(frozen=True, slots=True)
class ProcessMonitorConfig:
    """Group all configuration required for process monitoring."""

    collection: ProcessCollectionConfig
    processes: tuple[ProcessTargetConfig, ...]
    report: ProcessReportConfig

    def __post_init__(self) -> None:
        """Validate the complete process monitor configuration."""
        if not isinstance(self.collection, ProcessCollectionConfig):
            raise TypeError(
                "collection must be a ProcessCollectionConfig instance."
            )

        if not isinstance(self.processes, tuple):
            raise TypeError("processes must be a tuple.")

        if not self.processes:
            raise ValueError(
                "At least one process must be configured."
            )

        for process in self.processes:
            if not isinstance(process, ProcessTargetConfig):
                raise TypeError(
                    "Every process must be a "
                    "ProcessTargetConfig instance."
                )

        process_names = [
            process.process_name.casefold()
            for process in self.processes
        ]

        if len(process_names) != len(set(process_names)):
            raise ValueError(
                "Configured process names must be unique."
            )

        if not isinstance(self.report, ProcessReportConfig):
            raise TypeError(
                "report must be a ProcessReportConfig instance."
            )