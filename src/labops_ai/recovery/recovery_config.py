"""Validated configuration for safe recovery actions."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from labops_ai.health_status import HealthStatus


_ACTION_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9-]{2,63}$"
)
_SERVICE_UNIT_PATTERN = re.compile(
    r"^[A-Za-z0-9_.@:-]+\.service$"
)


def _normalize_boolean(
    field_name: str,
    value: object,
) -> bool:
    """Validate one required Boolean field."""
    if not isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be a Boolean."
        )

    return value


def _normalize_number(
    field_name: str,
    value: object,
    *,
    minimum: float,
    maximum: float,
) -> float:
    """Validate one bounded finite numeric field."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise TypeError(
            f"{field_name} must be numeric."
        )

    normalized_value = float(value)

    if not math.isfinite(normalized_value):
        raise ValueError(
            f"{field_name} must be finite."
        )

    if not minimum <= normalized_value <= maximum:
        raise ValueError(
            f"{field_name} must be between "
            f"{minimum} and {maximum}."
        )

    return normalized_value


def _normalize_integer(
    field_name: str,
    value: object,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Validate one bounded integer field."""
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(
            f"{field_name} must be an integer."
        )

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{field_name} must be between "
            f"{minimum} and {maximum}."
        )

    return value


def _normalize_action_id(value: object) -> str:
    """Validate one stable recovery action identifier."""
    if not isinstance(value, str):
        raise TypeError(
            "Recovery action ID must be a string."
        )

    normalized_value = value.strip()

    if not _ACTION_ID_PATTERN.fullmatch(
        normalized_value
    ):
        raise ValueError(
            "Recovery action ID must use lowercase "
            "letters, digits, and hyphens."
        )

    return normalized_value


def _normalize_service_unit(value: object) -> str:
    """Validate one allowlisted systemd service unit."""
    if not isinstance(value, str):
        raise TypeError(
            "Recovery service unit must be a string."
        )

    normalized_value = value.strip()

    if not _SERVICE_UNIT_PATTERN.fullmatch(
        normalized_value
    ):
        raise ValueError(
            "Recovery service unit must be a valid "
            "*.service unit without paths or whitespace."
        )

    return normalized_value


@dataclass(frozen=True, slots=True)
class RecoveryExecutionConfig:
    """Control safe execution limits for recovery."""

    enabled: bool
    dry_run: bool
    command_timeout_seconds: float
    cooldown_seconds: int
    max_actions_per_run: int

    def __post_init__(self) -> None:
        """Validate global recovery execution limits."""
        enabled = _normalize_boolean(
            "Recovery enabled flag",
            self.enabled,
        )
        dry_run = _normalize_boolean(
            "Recovery dry-run flag",
            self.dry_run,
        )
        timeout = _normalize_number(
            "Recovery command timeout",
            self.command_timeout_seconds,
            minimum=1.0,
            maximum=300.0,
        )
        cooldown = _normalize_integer(
            "Recovery cooldown seconds",
            self.cooldown_seconds,
            minimum=0,
            maximum=86400,
        )
        maximum_actions = _normalize_integer(
            "Recovery maximum actions per run",
            self.max_actions_per_run,
            minimum=1,
            maximum=20,
        )

        object.__setattr__(self, "enabled", enabled)
        object.__setattr__(self, "dry_run", dry_run)
        object.__setattr__(
            self,
            "command_timeout_seconds",
            timeout,
        )
        object.__setattr__(
            self,
            "cooldown_seconds",
            cooldown,
        )
        object.__setattr__(
            self,
            "max_actions_per_run",
            maximum_actions,
        )


@dataclass(frozen=True, slots=True)
class ServiceRecoveryRule:
    """Allow one explicit systemd service recovery."""

    action_id: str
    unit: str
    enabled: bool
    trigger_statuses: tuple[HealthStatus, ...]

    def __post_init__(self) -> None:
        """Validate the allowlisted service rule."""
        action_id = _normalize_action_id(
            self.action_id
        )
        unit = _normalize_service_unit(self.unit)
        enabled = _normalize_boolean(
            "Service recovery enabled flag",
            self.enabled,
        )

        if not isinstance(
            self.trigger_statuses,
            tuple,
        ):
            raise TypeError(
                "Recovery trigger statuses must be a tuple."
            )

        if not self.trigger_statuses:
            raise ValueError(
                "Recovery trigger statuses must not be empty."
            )

        if any(
            not isinstance(status, HealthStatus)
            for status in self.trigger_statuses
        ):
            raise TypeError(
                "Every recovery trigger status must be "
                "a HealthStatus."
            )

        if HealthStatus.HEALTHY in self.trigger_statuses:
            raise ValueError(
                "HEALTHY cannot trigger a recovery action."
            )

        if len(set(self.trigger_statuses)) != len(
            self.trigger_statuses
        ):
            raise ValueError(
                "Recovery trigger statuses must be unique."
            )

        object.__setattr__(
            self,
            "action_id",
            action_id,
        )
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "enabled", enabled)


@dataclass(frozen=True, slots=True)
class RecoveryConfig:
    """Represent complete recovery configuration."""

    execution: RecoveryExecutionConfig
    service_rules: tuple[ServiceRecoveryRule, ...]

    def __post_init__(self) -> None:
        """Validate recovery dependencies and rules."""
        if not isinstance(
            self.execution,
            RecoveryExecutionConfig,
        ):
            raise TypeError(
                "execution must be a "
                "RecoveryExecutionConfig instance."
            )

        if not isinstance(self.service_rules, tuple):
            raise TypeError(
                "service_rules must be a tuple."
            )

        if not self.service_rules:
            raise ValueError(
                "At least one service recovery rule "
                "must be configured."
            )

        if any(
            not isinstance(rule, ServiceRecoveryRule)
            for rule in self.service_rules
        ):
            raise TypeError(
                "Every service recovery rule must be a "
                "ServiceRecoveryRule instance."
            )

        action_ids = [
            rule.action_id
            for rule in self.service_rules
        ]
        units = [
            rule.unit.casefold()
            for rule in self.service_rules
        ]

        if len(set(action_ids)) != len(action_ids):
            raise ValueError(
                "Recovery action IDs must be unique."
            )

        if len(set(units)) != len(units):
            raise ValueError(
                "Recovery service units must be unique."
            )
