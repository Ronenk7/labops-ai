"""Result and state models for safe recovery actions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from labops_ai.health_status import HealthStatus


class RecoveryActionOutcome(StrEnum):
    """Define normalized recovery action outcomes."""

    SKIPPED_DISABLED = "SKIPPED_DISABLED"
    SKIPPED_RULE_DISABLED = "SKIPPED_RULE_DISABLED"
    SKIPPED_NOT_TRIGGERED = "SKIPPED_NOT_TRIGGERED"
    SKIPPED_COOLDOWN = "SKIPPED_COOLDOWN"
    SKIPPED_LIMIT = "SKIPPED_LIMIT"
    DRY_RUN = "DRY_RUN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


def _normalize_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and normalize a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must contain timezone information."
        )

    return value.astimezone(timezone.utc)


def _normalize_required_string(
    field_name: str,
    value: object,
) -> str:
    """Validate and normalize one required string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


@dataclass(frozen=True, slots=True)
class RecoveryActionResult:
    """Represent one planned or executed recovery action."""

    action_id: str
    unit: str
    health_status: HealthStatus
    outcome: RecoveryActionOutcome
    details: str
    attempted_at: datetime

    def __post_init__(self) -> None:
        """Validate and normalize the action result."""
        if not isinstance(
            self.health_status,
            HealthStatus,
        ):
            raise TypeError(
                "health_status must be a HealthStatus."
            )

        if not isinstance(
            self.outcome,
            RecoveryActionOutcome,
        ):
            raise TypeError(
                "outcome must be a RecoveryActionOutcome."
            )

        object.__setattr__(
            self,
            "action_id",
            _normalize_required_string(
                "Recovery action ID",
                self.action_id,
            ),
        )
        object.__setattr__(
            self,
            "unit",
            _normalize_required_string(
                "Recovery service unit",
                self.unit,
            ),
        )
        object.__setattr__(
            self,
            "details",
            _normalize_required_string(
                "Recovery result details",
                self.details,
            ),
        )
        object.__setattr__(
            self,
            "attempted_at",
            _normalize_aware_datetime(
                "Recovery action time",
                self.attempted_at,
            ),
        )


@dataclass(frozen=True, slots=True)
class RecoveryRunSummary:
    """Summarize all recovery decisions from one run."""

    results: tuple[RecoveryActionResult, ...]

    def __post_init__(self) -> None:
        """Validate the result collection."""
        if not isinstance(self.results, tuple):
            raise TypeError("results must be a tuple.")

        if any(
            not isinstance(
                result,
                RecoveryActionResult,
            )
            for result in self.results
        ):
            raise TypeError(
                "Every recovery result must be a "
                "RecoveryActionResult."
            )

    @property
    def attempted_count(self) -> int:
        """Return commands actually attempted."""
        attempted_outcomes = {
            RecoveryActionOutcome.SUCCEEDED,
            RecoveryActionOutcome.FAILED,
            RecoveryActionOutcome.TIMED_OUT,
        }
        return sum(
            result.outcome in attempted_outcomes
            for result in self.results
        )

    @property
    def successful_count(self) -> int:
        """Return successful command count."""
        return sum(
            result.outcome
            is RecoveryActionOutcome.SUCCEEDED
            for result in self.results
        )

    @property
    def dry_run_count(self) -> int:
        """Return dry-run action count."""
        return sum(
            result.outcome
            is RecoveryActionOutcome.DRY_RUN
            for result in self.results
        )


@dataclass(frozen=True, slots=True)
class RecoveryActionState:
    """Persist the last actual attempt for one action."""

    action_id: str
    last_attempted_at: datetime

    def __post_init__(self) -> None:
        """Validate persisted action state."""
        object.__setattr__(
            self,
            "action_id",
            _normalize_required_string(
                "Recovery action ID",
                self.action_id,
            ),
        )
        object.__setattr__(
            self,
            "last_attempted_at",
            _normalize_aware_datetime(
                "Recovery last attempt time",
                self.last_attempted_at,
            ),
        )


@dataclass(frozen=True, slots=True)
class RecoveryState:
    """Represent all persisted recovery cooldown data."""

    actions: tuple[RecoveryActionState, ...] = ()

    def __post_init__(self) -> None:
        """Validate unique persisted action identifiers."""
        if not isinstance(self.actions, tuple):
            raise TypeError("actions must be a tuple.")

        if any(
            not isinstance(action, RecoveryActionState)
            for action in self.actions
        ):
            raise TypeError(
                "Every recovery state item must be a "
                "RecoveryActionState."
            )

        action_ids = [
            action.action_id.casefold()
            for action in self.actions
        ]

        if len(action_ids) != len(set(action_ids)):
            raise ValueError(
                "Recovery state action IDs must be unique."
            )

    def get_last_attempt(
        self,
        action_id: str,
    ) -> datetime | None:
        """Return the last attempt for one action."""
        normalized_id = _normalize_required_string(
            "Recovery action ID",
            action_id,
        ).casefold()

        for action in self.actions:
            if action.action_id.casefold() == normalized_id:
                return action.last_attempted_at

        return None

    def with_attempt(
        self,
        action_id: str,
        attempted_at: datetime,
    ) -> RecoveryState:
        """Return state updated with one action attempt."""
        normalized_id = _normalize_required_string(
            "Recovery action ID",
            action_id,
        )
        normalized_time = _normalize_aware_datetime(
            "Recovery action time",
            attempted_at,
        )

        remaining = tuple(
            action
            for action in self.actions
            if action.action_id.casefold()
            != normalized_id.casefold()
        )

        return RecoveryState(
            actions=remaining
            + (
                RecoveryActionState(
                    action_id=normalized_id,
                    last_attempted_at=normalized_time,
                ),
            )
        )
