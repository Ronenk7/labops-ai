"""Validated formatting configuration for incident signals."""
from __future__ import annotations

from dataclasses import dataclass
from string import Formatter


_TEMPLATE_FIELDS = {
    "system_description_template": {
        "label",
        "value",
        "severity",
    },
    "network_label_template": {
        "check_type",
        "target",
    },
    "network_success_description_template": {
        "check_type",
        "target",
        "latency_ms",
        "severity",
    },
    "network_failure_description_template": {
        "check_type",
        "target",
        "severity",
        "details",
    },
    "service_state_description_template": {
        "label",
        "status",
        "severity",
        "load_state",
        "active_state",
        "sub_state",
    },
    "service_failure_description_template": {
        "label",
        "status",
        "severity",
        "details",
    },
    "process_running_description_template": {
        "label",
        "status",
        "severity",
        "instances",
        "cpu_percent",
        "memory_mb",
        "longest_runtime_seconds",
    },
    "process_not_running_description_template": {
        "label",
        "status",
        "severity",
    },
    "process_failure_description_template": {
        "label",
        "status",
        "severity",
        "details",
    },
    "log_analyzed_description_template": {
        "label",
        "status",
        "severity",
        "lines_scanned",
        "matches",
    },
    "log_failure_description_template": {
        "label",
        "status",
        "severity",
        "details",
    },
    "failure_reason_template": {
        "reason",
    },
    "failure_with_message_template": {
        "reason",
        "message",
    },
}


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


def _validate_template(
    field_name: str,
    template: object,
    required_fields: set[str],
) -> str:
    """Validate one configured formatting template."""
    normalized_template = _normalize_non_empty_string(
        field_name.replace("_", " ").title(),
        template,
    )

    try:
        parsed_fields = {
            parsed_field
            for _, parsed_field, _, _ in Formatter().parse(
                normalized_template
            )
            if parsed_field is not None
        }
    except ValueError as error:
        raise ValueError(
            f"{field_name} contains invalid formatting syntax."
        ) from error

    if parsed_fields != required_fields:
        expected = ", ".join(sorted(required_fields))
        received = ", ".join(sorted(parsed_fields))

        raise ValueError(
            f"{field_name} must contain exactly these fields: "
            f"{expected}. Received: {received or 'none'}."
        )

    return normalized_template


@dataclass(frozen=True, slots=True)
class IncidentSignalFactoryConfig:
    """Represent externally configured incident signal text."""

    decimal_places: int
    system_description_template: str
    network_label_template: str
    network_success_description_template: str
    network_failure_description_template: str
    service_state_description_template: str
    service_failure_description_template: str
    process_running_description_template: str
    process_not_running_description_template: str
    process_failure_description_template: str
    log_analyzed_description_template: str
    log_failure_description_template: str
    failure_reason_template: str
    failure_with_message_template: str

    def __post_init__(self) -> None:
        """Validate numeric formatting and every template."""
        if isinstance(self.decimal_places, bool) or not isinstance(
            self.decimal_places,
            int,
        ):
            raise TypeError(
                "Incident signal decimal places must be an integer."
            )

        if not 0 <= self.decimal_places <= 6:
            raise ValueError(
                "Incident signal decimal places must be "
                "between 0 and 6."
            )

        for field_name, required_fields in _TEMPLATE_FIELDS.items():
            normalized_template = _validate_template(
                field_name=field_name,
                template=getattr(self, field_name),
                required_fields=required_fields,
            )
            object.__setattr__(
                self,
                field_name,
                normalized_template,
            )