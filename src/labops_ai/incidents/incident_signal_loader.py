"""Load incident signal formatting from external JSON."""
from __future__ import annotations

from pathlib import Path

from labops_ai.config.utils import (
    INCIDENT_SIGNALS_CONFIG_PATH,
    load_json_config,
)
from labops_ai.incidents.incident_signal_config import (
    IncidentSignalFactoryConfig,
)


_REQUIRED_KEYS = {
    "decimal_places",
    "system_description_template",
    "network_label_template",
    "network_success_description_template",
    "network_failure_description_template",
    "service_state_description_template",
    "service_failure_description_template",
    "process_running_description_template",
    "process_not_running_description_template",
    "process_failure_description_template",
    "log_analyzed_description_template",
    "log_failure_description_template",
    "failure_reason_template",
    "failure_with_message_template",
}


class IncidentSignalConfigLoader:
    """Load and validate incident signal configuration."""

    def __init__(
        self,
        config_path: str | Path = INCIDENT_SIGNALS_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> IncidentSignalFactoryConfig:
        """Load JSON into a validated signal factory model."""
        configuration = load_json_config(self._config_path)
        self._validate_exact_keys(configuration)

        return IncidentSignalFactoryConfig(**configuration)

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, object],
    ) -> None:
        """Reject missing and unsupported configuration keys."""
        configuration_keys = set(configuration)
        missing_keys = _REQUIRED_KEYS - configuration_keys
        unexpected_keys = configuration_keys - _REQUIRED_KEYS

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise ValueError(
                "Missing required keys in incident signal "
                f"configuration: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                "Unsupported keys in incident signal "
                f"configuration: {formatted_keys}."
            )