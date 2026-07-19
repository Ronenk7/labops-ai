"""Plan and execute safe service recovery actions."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from labops_ai.recovery.recovery_config import (
    RecoveryConfig,
    ServiceRecoveryRule,
)
from labops_ai.recovery.recovery_executor import (
    ServiceRestartOutcome,
    SystemctlRecoveryExecutor,
)
from labops_ai.recovery.recovery_models import (
    RecoveryActionOutcome,
    RecoveryActionResult,
    RecoveryRunSummary,
    RecoveryState,
)
from labops_ai.services import (
    ServiceHealthRecord,
    ServiceMonitoringSummary,
)


class RecoveryStateStore(Protocol):
    """Define recovery state persistence operations."""

    def load(self) -> RecoveryState:
        """Load recovery state."""

    def save(self, state: RecoveryState) -> None:
        """Save recovery state."""


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RecoveryManager:
    """Apply configured recovery rules to service health."""

    config: RecoveryConfig
    executor: SystemctlRecoveryExecutor
    state_store: RecoveryStateStore
    clock: Callable[[], datetime] = _utc_now

    def __post_init__(self) -> None:
        """Validate recovery dependencies."""
        if not isinstance(self.config, RecoveryConfig):
            raise TypeError(
                "config must be a RecoveryConfig."
            )

        if not isinstance(
            self.executor,
            SystemctlRecoveryExecutor,
        ):
            raise TypeError(
                "executor must be a "
                "SystemctlRecoveryExecutor."
            )

        if not callable(
            getattr(self.state_store, "load", None)
        ) or not callable(
            getattr(self.state_store, "save", None)
        ):
            raise TypeError(
                "state_store must provide load and save."
            )

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def run(
        self,
        summary: ServiceMonitoringSummary,
    ) -> RecoveryRunSummary:
        """Evaluate and optionally execute recovery actions."""
        if not isinstance(
            summary,
            ServiceMonitoringSummary,
        ):
            raise TypeError(
                "summary must be a "
                "ServiceMonitoringSummary."
            )

        attempted_at = self.clock()

        if (
            not isinstance(attempted_at, datetime)
            or attempted_at.tzinfo is None
            or attempted_at.utcoffset() is None
        ):
            raise ValueError(
                "Recovery clock must return a "
                "timezone-aware datetime."
            )

        attempted_at = attempted_at.astimezone(
            timezone.utc
        )
        state = self.state_store.load()

        if not isinstance(state, RecoveryState):
            raise TypeError(
                "Recovery state store must return "
                "RecoveryState."
            )

        records = {
            record.result.service_name.casefold(): record
            for record in summary.records
        }
        results: list[RecoveryActionResult] = []
        actual_attempts = 0
        state_changed = False

        for rule in self.config.service_rules:
            record = records.get(
                rule.unit.casefold()
            )

            if record is None:
                continue

            result = self._process_rule(
                rule=rule,
                record=record,
                state=state,
                attempted_at=attempted_at,
                actual_attempts=actual_attempts,
            )
            results.append(result)

            if result.outcome in {
                RecoveryActionOutcome.SUCCEEDED,
                RecoveryActionOutcome.FAILED,
                RecoveryActionOutcome.TIMED_OUT,
            }:
                actual_attempts += 1
                state = state.with_attempt(
                    rule.action_id,
                    attempted_at,
                )
                state_changed = True

        if state_changed:
            self.state_store.save(state)

        return RecoveryRunSummary(
            results=tuple(results)
        )

    def _process_rule(
        self,
        *,
        rule: ServiceRecoveryRule,
        record: ServiceHealthRecord,
        state: RecoveryState,
        attempted_at: datetime,
        actual_attempts: int,
    ) -> RecoveryActionResult:
        """Evaluate and possibly execute one rule."""
        if not rule.enabled:
            return self._result(
                rule,
                record,
                RecoveryActionOutcome.SKIPPED_RULE_DISABLED,
                "Recovery rule is disabled.",
                attempted_at,
            )

        if (
            record.health_status
            not in rule.trigger_statuses
        ):
            return self._result(
                rule,
                record,
                RecoveryActionOutcome.SKIPPED_NOT_TRIGGERED,
                "Service health does not trigger recovery.",
                attempted_at,
            )

        if not self.config.execution.enabled:
            return self._result(
                rule,
                record,
                RecoveryActionOutcome.SKIPPED_DISABLED,
                "Recovery execution is globally disabled.",
                attempted_at,
            )

        last_attempt = state.get_last_attempt(
            rule.action_id
        )

        if last_attempt is not None:
            next_allowed = last_attempt + timedelta(
                seconds=(
                    self.config.execution.cooldown_seconds
                )
            )

            if attempted_at < next_allowed:
                return self._result(
                    rule,
                    record,
                    RecoveryActionOutcome.SKIPPED_COOLDOWN,
                    (
                        "Recovery action remains inside "
                        "its cooldown period."
                    ),
                    attempted_at,
                )

        if actual_attempts >= (
            self.config.execution.max_actions_per_run
        ):
            return self._result(
                rule,
                record,
                RecoveryActionOutcome.SKIPPED_LIMIT,
                "Maximum recovery actions reached.",
                attempted_at,
            )

        if self.config.execution.dry_run:
            return self._result(
                rule,
                record,
                RecoveryActionOutcome.DRY_RUN,
                (
                    "Dry run: systemctl restart "
                    f"{rule.unit}"
                ),
                attempted_at,
            )

        command_result = self.executor.restart(
            rule.unit,
            timeout_seconds=(
                self.config.execution
                .command_timeout_seconds
            ),
        )
        outcome_map = {
            ServiceRestartOutcome.SUCCEEDED: (
                RecoveryActionOutcome.SUCCEEDED
            ),
            ServiceRestartOutcome.FAILED: (
                RecoveryActionOutcome.FAILED
            ),
            ServiceRestartOutcome.TIMED_OUT: (
                RecoveryActionOutcome.TIMED_OUT
            ),
        }

        return self._result(
            rule,
            record,
            outcome_map[command_result.outcome],
            command_result.details,
            attempted_at,
        )

    @staticmethod
    def _result(
        rule: ServiceRecoveryRule,
        record: ServiceHealthRecord,
        outcome: RecoveryActionOutcome,
        details: str,
        attempted_at: datetime,
    ) -> RecoveryActionResult:
        """Build one normalized recovery result."""
        return RecoveryActionResult(
            action_id=rule.action_id,
            unit=rule.unit,
            health_status=record.health_status,
            outcome=outcome,
            details=details,
            attempted_at=attempted_at,
        )
