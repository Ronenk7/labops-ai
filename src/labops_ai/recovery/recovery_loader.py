"""Load safe recovery configuration from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    RECOVERY_ACTIONS_CONFIG_PATH,
    load_json_config,
)
from labops_ai.health_status import HealthStatus
from labops_ai.recovery.recovery_config import (
    RecoveryConfig,
    RecoveryExecutionConfig,
    ServiceRecoveryRule,
)


class RecoveryConfigLoader:
    """Load and validate recovery action configuration."""

    def __init__(
        self,
        config_path: str | Path = (
            RECOVERY_ACTIONS_CONFIG_PATH
        ),
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> RecoveryConfig:
        """Load validated recovery configuration."""
        configuration = load_json_config(
            self._config_path
        )
        self._validate_configuration(configuration)

        service_rules = tuple(
            ServiceRecoveryRule(
                action_id=rule["action_id"],
                unit=rule["unit"],
                enabled=rule["enabled"],
                trigger_statuses=tuple(
                    self._parse_status(status)
                    for status in rule[
                        "trigger_statuses"
                    ]
                ),
            )
            for rule in configuration[
                "service_rules"
            ]
        )

        return RecoveryConfig(
            execution=RecoveryExecutionConfig(
                **configuration["execution"]
            ),
            service_rules=service_rules,
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate required JSON sections and keys."""
        cls._validate_exact_keys(
            configuration,
            {"execution", "service_rules"},
            "configuration",
        )

        execution = cls._require_object(
            configuration,
            "execution",
        )
        service_rules = cls._require_array(
            configuration,
            "service_rules",
        )

        cls._validate_exact_keys(
            execution,
            {
                "enabled",
                "dry_run",
                "command_timeout_seconds",
                "cooldown_seconds",
                "max_actions_per_run",
            },
            "execution section",
        )

        for index, rule in enumerate(service_rules):
            if not isinstance(rule, dict):
                raise ValueError(
                    "Every service recovery rule "
                    "must be a JSON object."
                )

            cls._validate_exact_keys(
                rule,
                {
                    "action_id",
                    "unit",
                    "enabled",
                    "trigger_statuses",
                },
                f"service rule {index}",
            )

            statuses = rule["trigger_statuses"]

            if not isinstance(statuses, list):
                raise ValueError(
                    "Recovery trigger statuses "
                    "must be a JSON array."
                )

    @staticmethod
    def _parse_status(value: object) -> HealthStatus:
        """Convert one configured trigger status."""
        if not isinstance(value, str):
            raise TypeError(
                "Recovery trigger status must be a string."
            )

        try:
            return HealthStatus(value.strip().upper())
        except ValueError as error:
            raise ValueError(
                "Unsupported recovery trigger status: "
                f"{value}."
            ) from error

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return one required JSON object section."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Recovery section '{section_name}' "
                "must be a JSON object."
            )

        return section

    @staticmethod
    def _require_array(
        configuration: dict[str, Any],
        section_name: str,
    ) -> list[Any]:
        """Return one required JSON array section."""
        section = configuration[section_name]

        if not isinstance(section, list):
            raise ValueError(
                f"Recovery section '{section_name}' "
                "must be a JSON array."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing or unsupported JSON keys."""
        keys = set(configuration)
        missing = required_keys - keys
        unexpected = keys - required_keys

        if missing:
            formatted = ", ".join(sorted(missing))
            raise ValueError(
                "Missing required keys in recovery "
                f"{location}: {formatted}."
            )

        if unexpected:
            formatted = ", ".join(sorted(unexpected))
            raise ValueError(
                "Unsupported keys in recovery "
                f"{location}: {formatted}."
            )
