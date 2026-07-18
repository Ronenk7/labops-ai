"""Validated configuration models for Linux service monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _normalize_non_empty_string(
    field_name: str,
    value: object,
) -> str:
    """Validate and normalize a required string value."""
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
class ServiceTargetConfig:
    """Represent one configured Linux service unit."""

    service_name: str
    label: str

    def __post_init__(self) -> None:
        """Validate and normalize the service target."""
        normalized_name = _normalize_non_empty_string(
            "Service name",
            self.service_name,
        )
        normalized_label = _normalize_non_empty_string(
            "Service label",
            self.label,
        )

        if any(character.isspace() for character in normalized_name):
            raise ValueError(
                "Service name must not contain whitespace."
            )

        if not normalized_name.endswith(".service"):
            raise ValueError(
                "Service name must end with '.service'."
            )

        object.__setattr__(self, "service_name", normalized_name)
        object.__setattr__(self, "label", normalized_label)


@dataclass(frozen=True, slots=True)
class SystemctlCommandConfig:
    """Represent external systemctl command settings."""

    executable: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate and normalize command settings."""
        normalized_executable = _normalize_non_empty_string(
            "Systemctl executable",
            self.executable,
        )
        normalized_timeout = _normalize_positive_number(
            "Systemctl timeout",
            self.timeout_seconds,
        )

        object.__setattr__(self, "executable", normalized_executable)
        object.__setattr__(self, "timeout_seconds", normalized_timeout)


@dataclass(frozen=True, slots=True)
class ServiceReportConfig:
    """Represent externally configured service report text."""

    title: str
    separator: str
    overall_label: str
    service_label: str
    unit_label: str
    health_label: str
    load_state_label: str
    active_state_label: str
    sub_state_label: str
    failure_reason_label: str
    error_message_label: str

    def __post_init__(self) -> None:
        """Validate and normalize every report label."""
        for field_name in self.__dataclass_fields__:
            normalized_value = _normalize_non_empty_string(
                field_name.replace("_", " ").title(),
                getattr(self, field_name),
            )
            object.__setattr__(self, field_name, normalized_value)


@dataclass(frozen=True, slots=True)
class ServiceMonitorConfig:
    """Group all configuration required for service monitoring."""

    command: SystemctlCommandConfig
    services: tuple[ServiceTargetConfig, ...]
    report: ServiceReportConfig

    def __post_init__(self) -> None:
        """Validate complete service monitor configuration."""
        if not isinstance(self.command, SystemctlCommandConfig):
            raise TypeError(
                "command must be a SystemctlCommandConfig instance."
            )

        if not isinstance(self.services, tuple):
            raise TypeError("services must be a tuple.")

        if not self.services:
            raise ValueError(
                "At least one service must be configured."
            )

        for service in self.services:
            if not isinstance(service, ServiceTargetConfig):
                raise TypeError(
                    "Every service must be a ServiceTargetConfig instance."
                )

        service_names = [
            service.service_name
            for service in self.services
        ]

        if len(service_names) != len(set(service_names)):
            raise ValueError(
                "Configured service names must be unique."
            )

        if not isinstance(self.report, ServiceReportConfig):
            raise TypeError(
                "report must be a ServiceReportConfig instance."
            )