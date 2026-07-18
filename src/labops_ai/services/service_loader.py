"""Load Linux service monitoring settings from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    SERVICE_MONITOR_CONFIG_PATH,
    load_json_config,
)
from labops_ai.services.service_config import (
    ServiceMonitorConfig,
    ServiceReportConfig,
    ServiceTargetConfig,
    SystemctlCommandConfig,
)


class ServiceMonitorConfigLoader:
    """Load and validate service monitor configuration."""

    def __init__(
        self,
        config_path: str | Path = SERVICE_MONITOR_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a configuration path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON file path."""
        return self._config_path

    def load(self) -> ServiceMonitorConfig:
        """Load and convert external JSON into validated models."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        command_values = configuration["command"]
        service_values = configuration["services"]
        report_values = configuration["report"]

        services = tuple(
            ServiceTargetConfig(
                service_name=service["service_name"],
                label=service["label"],
            )
            for service in service_values
        )

        return ServiceMonitorConfig(
            command=SystemctlCommandConfig(
                executable=command_values["executable"],
                timeout_seconds=command_values["timeout_seconds"],
            ),
            services=services,
            report=ServiceReportConfig(
                title=report_values["title"],
                separator=report_values["separator"],
                overall_label=report_values["overall_label"],
                service_label=report_values["service_label"],
                unit_label=report_values["unit_label"],
                health_label=report_values["health_label"],
                load_state_label=report_values["load_state_label"],
                active_state_label=report_values[
                    "active_state_label"
                ],
                sub_state_label=report_values["sub_state_label"],
                failure_reason_label=report_values[
                    "failure_reason_label"
                ],
                error_message_label=report_values[
                    "error_message_label"
                ],
            ),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate required JSON sections and exact keys."""
        cls._validate_exact_keys(
            configuration,
            {"command", "services", "report"},
            "configuration",
        )

        command = cls._require_object(
            configuration,
            "command",
            "configuration",
        )
        services = cls._require_list(
            configuration,
            "services",
            "configuration",
        )
        report = cls._require_object(
            configuration,
            "report",
            "configuration",
        )

        cls._validate_exact_keys(
            command,
            {"executable", "timeout_seconds"},
            "command section",
        )

        cls._validate_exact_keys(
            report,
            {
                "title",
                "separator",
                "overall_label",
                "service_label",
                "unit_label",
                "health_label",
                "load_state_label",
                "active_state_label",
                "sub_state_label",
                "failure_reason_label",
                "error_message_label",
            },
            "report section",
        )

        if not services:
            raise ValueError(
                "Service monitor services section must not be empty."
            )

        for index, service in enumerate(services):
            if not isinstance(service, dict):
                raise ValueError(
                    f"Service entry {index} must be a JSON object."
                )

            cls._validate_exact_keys(
                service,
                {"service_name", "label"},
                f"service entry {index}",
            )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
        location: str,
    ) -> dict[str, Any]:
        """Return a required JSON object."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Service monitor {location} '{section_name}' "
                "must be a JSON object."
            )

        return section

    @staticmethod
    def _require_list(
        configuration: dict[str, Any],
        section_name: str,
        location: str,
    ) -> list[Any]:
        """Return a required JSON array."""
        section = configuration[section_name]

        if not isinstance(section, list):
            raise ValueError(
                f"Service monitor {location} '{section_name}' "
                "must be a JSON array."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported JSON keys."""
        configuration_keys = set(configuration)
        missing_keys = required_keys - configuration_keys
        unexpected_keys = configuration_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise ValueError(
                f"Missing required keys in service monitor "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                f"Unsupported keys in service monitor "
                f"{location}: {formatted_keys}."
            )