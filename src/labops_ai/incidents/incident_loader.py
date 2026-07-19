"""Load incident management settings from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    INCIDENT_MANAGEMENT_CONFIG_PATH,
    load_json_config,
)
from labops_ai.incidents.incident_config import (
    IncidentIdentifierConfig,
    IncidentManagementConfig,
    IncidentReportConfig,
    IncidentStorageConfig,
)


class IncidentManagementConfigLoader:
    """Load and validate incident management configuration."""

    def __init__(
        self,
        config_path: str | Path = INCIDENT_MANAGEMENT_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a JSON configuration path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> IncidentManagementConfig:
        """Load external JSON into validated incident models."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        storage_values = configuration["storage"]
        identifier_values = configuration["identifier"]
        report_values = configuration["report"]

        return IncidentManagementConfig(
            storage=IncidentStorageConfig(**storage_values),
            identifier=IncidentIdentifierConfig(
                **identifier_values
            ),
            report=IncidentReportConfig(**report_values),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate all required sections and exact keys."""
        cls._validate_exact_keys(
            configuration,
            {"storage", "identifier", "report"},
            "configuration",
        )

        storage = cls._require_object(
            configuration,
            "storage",
            "configuration",
        )
        identifier = cls._require_object(
            configuration,
            "identifier",
            "configuration",
        )
        report = cls._require_object(
            configuration,
            "report",
            "configuration",
        )

        cls._validate_exact_keys(
            storage,
            {"path"},
            "storage section",
        )
        cls._validate_exact_keys(
            identifier,
            {"prefix", "separator", "sequence_width"},
            "identifier section",
        )
        cls._validate_exact_keys(
            report,
            {
                "title",
                "separator",
                "actions_label",
                "created_label",
                "updated_label",
                "resolved_actions_label",
                "unchanged_label",
                "active_count_label",
                "resolved_count_label",
                "incident_label",
                "incident_id_label",
                "source_type_label",
                "source_id_label",
                "source_label",
                "severity_label",
                "status_label",
                "description_label",
                "first_seen_label",
                "last_seen_label",
                "occurrences_label",
                "resolved_at_label",
                "no_incidents_message",
            },
            "report section",
        )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
        location: str,
    ) -> dict[str, Any]:
        """Return one required JSON object."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Incident management {location} "
                f"'{section_name}' must be a JSON object."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported configuration keys."""
        configuration_keys = set(configuration)
        missing_keys = required_keys - configuration_keys
        unexpected_keys = configuration_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise ValueError(
                f"Missing required keys in incident management "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                f"Unsupported keys in incident management "
                f"{location}: {formatted_keys}."
            )