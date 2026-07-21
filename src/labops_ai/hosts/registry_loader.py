"""Load host-registry configuration from JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    HOST_REGISTRY_CONFIG_PATH,
    load_json_config,
)
from labops_ai.hosts.registry_config import (
    HostRegistryConfig,
    HostRegistryStorageConfig,
)
from labops_ai.hosts.status import (
    HostAvailabilityPolicy,
)


class HostRegistryConfigLoader:
    """Load and validate host-registry configuration."""

    def __init__(
        self,
        config_path: str | Path = (
            HOST_REGISTRY_CONFIG_PATH
        ),
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> HostRegistryConfig:
        """Load the complete registry configuration."""
        configuration = load_json_config(
            self._config_path
        )
        self._validate_configuration(configuration)

        return HostRegistryConfig(
            storage=HostRegistryStorageConfig(
                **configuration["storage"]
            ),
            availability=HostAvailabilityPolicy(
                **configuration["availability"]
            ),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate all required JSON sections."""
        cls._validate_exact_keys(
            configuration,
            {"storage", "availability"},
            "configuration",
        )

        storage = cls._require_object(
            configuration,
            "storage",
        )
        availability = cls._require_object(
            configuration,
            "availability",
        )

        cls._validate_exact_keys(
            storage,
            {
                "database_path",
                "busy_timeout_seconds",
            },
            "storage section",
        )
        cls._validate_exact_keys(
            availability,
            {
                "stale_after_seconds",
                "offline_after_seconds",
            },
            "availability section",
        )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return one required configuration section."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                "Host registry section "
                f"'{section_name}' must be "
                "a JSON object."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported keys."""
        actual_keys = set(configuration)
        missing = required_keys - actual_keys
        unexpected = actual_keys - required_keys

        if missing:
            formatted = ", ".join(sorted(missing))
            raise ValueError(
                "Missing required keys in host registry "
                f"{location}: {formatted}."
            )

        if unexpected:
            formatted = ", ".join(
                sorted(unexpected)
            )
            raise ValueError(
                "Unsupported keys in host registry "
                f"{location}: {formatted}."
            )
