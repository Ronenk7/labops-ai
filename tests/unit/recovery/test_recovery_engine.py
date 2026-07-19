"""Unit tests for the safe recovery engine."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.recovery import (
    JsonRecoveryStateStore,
    RecoveryActionOutcome,
    RecoveryConfig,
    RecoveryExecutionConfig,
    RecoveryManager,
    RecoveryState,
    ServiceRecoveryRule,
    SystemctlRecoveryExecutor,
    build_recovery_report,
)
from labops_ai.services import (
    ServiceCheckResult,
    ServiceCheckStatus,
    ServiceHealthRecord,
    ServiceMonitoringSummary,
)


pytestmark = pytest.mark.unit
NOW = datetime(
    2026,
    7,
    19,
    18,
    0,
    tzinfo=timezone.utc,
)


@dataclass
class MemoryStateStore:
    """Persist recovery state in memory for tests."""

    state: RecoveryState = RecoveryState()
    save_count: int = 0

    def load(self) -> RecoveryState:
        return self.state

    def save(self, state: RecoveryState) -> None:
        self.state = state
        self.save_count += 1


def build_summary(
    *units: str,
    health: HealthStatus = HealthStatus.CRITICAL,
) -> ServiceMonitoringSummary:
    records = tuple(
        ServiceHealthRecord(
            result=ServiceCheckResult(
                service_name=unit,
                label=unit,
                status=ServiceCheckStatus.FAILED,
                load_state="loaded",
                active_state="failed",
                sub_state="failed",
            ),
            health_status=health,
        )
        for unit in units
    )
    return ServiceMonitoringSummary(
        records=records,
        overall_status=health,
    )


def build_config(
    *,
    enabled: bool,
    dry_run: bool,
    max_actions: int = 3,
    rules: tuple[ServiceRecoveryRule, ...] | None = None,
) -> RecoveryConfig:
    return RecoveryConfig(
        execution=RecoveryExecutionConfig(
            enabled=enabled,
            dry_run=dry_run,
            command_timeout_seconds=10,
            cooldown_seconds=300,
            max_actions_per_run=max_actions,
        ),
        service_rules=rules
        or (
            ServiceRecoveryRule(
                action_id="restart-example",
                unit="example.service",
                enabled=True,
                trigger_statuses=(
                    HealthStatus.CRITICAL,
                ),
            ),
        ),
    )


class TestSystemctlRecoveryExecutor:
    def test_executes_exact_command_without_shell(
        self,
    ) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(
                returncode=0,
                stdout="restarted",
                stderr="",
            )

        result = SystemctlRecoveryExecutor(
            runner=runner
        ).restart(
            "example.service",
            timeout_seconds=10,
        )

        assert result.outcome.value == "SUCCEEDED"
        assert calls[0][0] == (
            "systemctl",
            "restart",
            "example.service",
        )
        assert "shell" not in calls[0][1]

    def test_reports_failed_command(self) -> None:
        result = SystemctlRecoveryExecutor(
            runner=lambda *args, **kwargs: (
                SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="permission denied",
                )
            )
        ).restart(
            "example.service",
            timeout_seconds=10,
        )

        assert result.outcome.value == "FAILED"
        assert "permission denied" in result.details

    def test_reports_timeout(self) -> None:
        def runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(
                cmd="systemctl",
                timeout=10,
            )

        result = SystemctlRecoveryExecutor(
            runner=runner
        ).restart(
            "example.service",
            timeout_seconds=10,
        )

        assert result.outcome.value == "TIMED_OUT"


class TestRecoveryManager:
    def test_global_disabled_prevents_command(
        self,
    ) -> None:
        calls = []
        manager = RecoveryManager(
            config=build_config(
                enabled=False,
                dry_run=False,
            ),
            executor=SystemctlRecoveryExecutor(
                runner=lambda *args, **kwargs: (
                    calls.append(args)
                )
            ),
            state_store=MemoryStateStore(),
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary("example.service")
        )

        assert summary.results[0].outcome is (
            RecoveryActionOutcome.SKIPPED_DISABLED
        )
        assert calls == []

    def test_dry_run_prevents_command_and_state_write(
        self,
    ) -> None:
        calls = []
        store = MemoryStateStore()
        manager = RecoveryManager(
            config=build_config(
                enabled=True,
                dry_run=True,
            ),
            executor=SystemctlRecoveryExecutor(
                runner=lambda *args, **kwargs: (
                    calls.append(args)
                )
            ),
            state_store=store,
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary("example.service")
        )

        assert summary.dry_run_count == 1
        assert calls == []
        assert store.save_count == 0

    def test_success_updates_cooldown_state(
        self,
    ) -> None:
        store = MemoryStateStore()
        manager = RecoveryManager(
            config=build_config(
                enabled=True,
                dry_run=False,
            ),
            executor=SystemctlRecoveryExecutor(
                runner=lambda *args, **kwargs: (
                    SimpleNamespace(
                        returncode=0,
                        stdout="",
                        stderr="",
                    )
                )
            ),
            state_store=store,
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary("example.service")
        )

        assert summary.successful_count == 1
        assert store.save_count == 1
        assert store.state.get_last_attempt(
            "restart-example"
        ) == NOW

    def test_cooldown_prevents_repeated_command(
        self,
    ) -> None:
        store = MemoryStateStore(
            state=RecoveryState().with_attempt(
                "restart-example",
                NOW,
            )
        )
        manager = RecoveryManager(
            config=build_config(
                enabled=True,
                dry_run=False,
            ),
            executor=SystemctlRecoveryExecutor(
                runner=lambda *args, **kwargs: (
                    pytest.fail(
                        "Command must not run."
                    )
                )
            ),
            state_store=store,
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary("example.service")
        )

        assert summary.results[0].outcome is (
            RecoveryActionOutcome.SKIPPED_COOLDOWN
        )

    def test_health_must_match_trigger(self) -> None:
        manager = RecoveryManager(
            config=build_config(
                enabled=True,
                dry_run=False,
            ),
            executor=SystemctlRecoveryExecutor(),
            state_store=MemoryStateStore(),
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary(
                "example.service",
                health=HealthStatus.WARNING,
            )
        )

        assert summary.results[0].outcome is (
            RecoveryActionOutcome
            .SKIPPED_NOT_TRIGGERED
        )

    def test_enforces_action_limit(self) -> None:
        rules = (
            ServiceRecoveryRule(
                action_id="restart-one",
                unit="one.service",
                enabled=True,
                trigger_statuses=(
                    HealthStatus.CRITICAL,
                ),
            ),
            ServiceRecoveryRule(
                action_id="restart-two",
                unit="two.service",
                enabled=True,
                trigger_statuses=(
                    HealthStatus.CRITICAL,
                ),
            ),
        )
        manager = RecoveryManager(
            config=build_config(
                enabled=True,
                dry_run=False,
                max_actions=1,
                rules=rules,
            ),
            executor=SystemctlRecoveryExecutor(
                runner=lambda *args, **kwargs: (
                    SimpleNamespace(
                        returncode=0,
                        stdout="",
                        stderr="",
                    )
                )
            ),
            state_store=MemoryStateStore(),
            clock=lambda: NOW,
        )

        summary = manager.run(
            build_summary(
                "one.service",
                "two.service",
            )
        )

        assert summary.attempted_count == 1
        assert summary.results[1].outcome is (
            RecoveryActionOutcome.SKIPPED_LIMIT
        )


class TestJsonRecoveryStateStore:
    def test_saves_and_loads_state(
        self,
        tmp_path: Path,
    ) -> None:
        store = JsonRecoveryStateStore(
            tmp_path / "recovery.json"
        )
        expected = RecoveryState().with_attempt(
            "restart-example",
            NOW,
        )

        store.save(expected)

        assert store.load() == expected

    def test_rejects_invalid_json(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "recovery.json"
        path.write_text("{ invalid", encoding="utf-8")

        with pytest.raises(
            RuntimeError,
            match="invalid JSON",
        ):
            JsonRecoveryStateStore(path).load()


def test_builds_recovery_report() -> None:
    manager = RecoveryManager(
        config=build_config(
            enabled=True,
            dry_run=True,
        ),
        executor=SystemctlRecoveryExecutor(),
        state_store=MemoryStateStore(),
        clock=lambda: NOW,
    )

    report = build_recovery_report(
        manager.run(
            build_summary("example.service")
        )
    )

    assert "Recovery Actions" in report
    assert "DRY_RUN" in report
