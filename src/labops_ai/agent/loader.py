"""Load remote host-agent configuration from JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.agent.config import (
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
)
from labops_ai.config.utils import (
    HOST_AGENT_CONFIG_PATH,
    load_json_config,
)


class HostAgentConfigLoader:
    """Load and validate host-agent configuration."""

    def __init__(
        self,
        config_path: str | Path = (
            HOST_AGENT_CONFIG_PATH
        ),
    ) -> None:
        """Initialize the loader."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> HostAgentConfig:
        """Load the complete Agent configuration."""
        configuration = load_json_config(
            self._config_path
        )
        self._validate_configuration(
            configuration
        )

        return HostAgentConfig(
            identity=HostAgentIdentityConfig(
                **configuration["identity"]
            ),
            server=HostAgentServerConfig(
                **configuration["server"]
            ),
            schedule=HostAgentScheduleConfig(
                **configuration["schedule"]
            ),
            retry=HostAgentRetryConfig(
                **configuration["retry"]
            ),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate required and optional settings."""
        cls._validate_exact_keys(
            configuration,
            {
                "identity",
                "server",
                "schedule",
                "retry",
            },
            "configuration",
        )

        required_sections = {
            "identity": {
                "host_id_override",
            },
            "server": {
                "base_url",
                "heartbeat_path",
                "request_timeout_seconds",
            },
            "schedule": {
                "interval_seconds",
            },
            "retry": {
                "max_attempts",
                "initial_backoff_seconds",
                "max_backoff_seconds",
            },
        }

        optional_sections = {
            "server": {
                "run_ingestion_path",
            },
            "schedule": {
                "monitoring_interval_seconds",
            },
        }

        for (
            section_name,
            required_keys,
        ) in required_sections.items():
            section = cls._require_object(
                configuration,
                section_name,
            )
            cls._validate_section_keys(
                section,
                required_keys=required_keys,
                optional_keys=optional_sections.get(
                    section_name,
                    set(),
                ),
                location=f"{section_name} section",
            )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return one required JSON object."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                "Host agent section "
                f"'{section_name}' must be "
                "a JSON object."
            )

        return section

    @staticmethod
    def _validate_section_keys(
        configuration: dict[str, Any],
        *,
        required_keys: set[str],
        optional_keys: set[str],
        location: str,
    ) -> None:
        """Validate required keys and reject unknown keys."""
        actual_keys = set(configuration)
        missing = required_keys - actual_keys
        unexpected = (
            actual_keys
            - required_keys
            - optional_keys
        )

        if missing:
            formatted = ", ".join(
                sorted(missing)
            )
            raise ValueError(
                "Missing required keys in host agent "
                f"{location}: {formatted}."
            )

        if unexpected:
            formatted = ", ".join(
                sorted(unexpected)
            )
            raise ValueError(
                "Unsupported keys in host agent "
                f"{location}: {formatted}."
            )

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        expected_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported keys."""
        actual_keys = set(configuration)
        missing = expected_keys - actual_keys
        unexpected = actual_keys - expected_keys

        if missing:
            formatted = ", ".join(
                sorted(missing)
            )
            raise ValueError(
                "Missing required keys in host agent "
                f"{location}: {formatted}."
            )

        if unexpected:
            formatted = ", ".join(
                sorted(unexpected)
            )
            raise ValueError(
                "Unsupported keys in host agent "
                f"{location}: {formatted}."
            )
