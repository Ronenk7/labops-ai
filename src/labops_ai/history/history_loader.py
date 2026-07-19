"""Load run history configuration from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    RUN_HISTORY_CONFIG_PATH,
    load_json_config,
)
from labops_ai.history.history_config import (
    RunHistoryConfig,
    RunHistoryRetentionConfig,
    RunHistoryStorageConfig,
)


class RunHistoryConfigLoader:
    """Load and validate run history configuration."""

    def __init__(
        self,
        config_path: str | Path = RUN_HISTORY_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> RunHistoryConfig:
        """Load JSON into validated run history settings."""
        configuration = load_json_config(
            self._config_path
        )
        self._validate_configuration(configuration)

        return RunHistoryConfig(
            storage=RunHistoryStorageConfig(
                **configuration["storage"]
            ),
            retention=RunHistoryRetentionConfig(
                **configuration["retention"]
            ),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate all required sections and nested keys."""
        cls._validate_exact_keys(
            configuration,
            {"storage", "retention"},
            "configuration",
        )

        storage = cls._require_object(
            configuration,
            "storage",
        )
        retention = cls._require_object(
            configuration,
            "retention",
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
            retention,
            {
                "max_runs",
                "max_age_days",
                "prune_on_write",
            },
            "retention section",
        )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return one required JSON object section."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Run history section '{section_name}' "
                "must be a JSON object."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported keys."""
        configuration_keys = set(configuration)
        missing_keys = required_keys - configuration_keys
        unexpected_keys = configuration_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(
                sorted(missing_keys)
            )
            raise ValueError(
                "Missing required keys in run history "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(
                sorted(unexpected_keys)
            )
            raise ValueError(
                "Unsupported keys in run history "
                f"{location}: {formatted_keys}."
            )
