"""Unit tests for recovery action configuration."""
from __future__ import annotations

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.recovery import (
    RecoveryConfig,
    RecoveryExecutionConfig,
    ServiceRecoveryRule,
)


pytestmark = pytest.mark.unit


def build_execution() -> RecoveryExecutionConfig:
    """Build valid recovery execution settings."""
    return RecoveryExecutionConfig(
        enabled=False,
        dry_run=True,
        command_timeout_seconds=30,
        cooldown_seconds=300,
        max_actions_per_run=3,
    )


def build_rule(
    *,
    action_id: str = "restart-example-service",
    unit: str = "example.service",
) -> ServiceRecoveryRule:
    """Build one valid service recovery rule."""
    return ServiceRecoveryRule(
        action_id=action_id,
        unit=unit,
        enabled=True,
        trigger_statuses=(
            HealthStatus.CRITICAL,
        ),
    )


class TestRecoveryExecutionConfig:
    """Test global recovery execution settings."""

    def test_accepts_valid_configuration(self) -> None:
        config = build_execution()

        assert config.enabled is False
        assert config.dry_run is True
        assert config.command_timeout_seconds == 30.0

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("enabled", "false"),
            ("dry_run", 1),
        ],
    )
    def test_rejects_invalid_boolean(
        self,
        field_name: str,
        value: object,
    ) -> None:
        values = {
            "enabled": False,
            "dry_run": True,
            "command_timeout_seconds": 30,
            "cooldown_seconds": 300,
            "max_actions_per_run": 3,
        }
        values[field_name] = value

        with pytest.raises(TypeError):
            RecoveryExecutionConfig(**values)

    @pytest.mark.parametrize(
        ("field_name", "value", "error"),
        [
            (
                "command_timeout_seconds",
                0,
                ValueError,
            ),
            (
                "command_timeout_seconds",
                "30",
                TypeError,
            ),
            ("cooldown_seconds", -1, ValueError),
            ("max_actions_per_run", 0, ValueError),
            ("max_actions_per_run", True, TypeError),
        ],
    )
    def test_rejects_invalid_limits(
        self,
        field_name: str,
        value: object,
        error: type[Exception],
    ) -> None:
        values = {
            "enabled": False,
            "dry_run": True,
            "command_timeout_seconds": 30,
            "cooldown_seconds": 300,
            "max_actions_per_run": 3,
        }
        values[field_name] = value

        with pytest.raises(error):
            RecoveryExecutionConfig(**values)


class TestServiceRecoveryRule:
    """Test explicit allowlisted service rules."""

    def test_accepts_valid_rule(self) -> None:
        rule = build_rule()

        assert rule.action_id == (
            "restart-example-service"
        )
        assert rule.unit == "example.service"

    def test_rejects_invalid_action_id(self) -> None:
        with pytest.raises(ValueError):
            build_rule(action_id="Restart Service")

    def test_rejects_invalid_service_unit(self) -> None:
        with pytest.raises(ValueError):
            build_rule(unit="/tmp/example.service")

    def test_rejects_healthy_trigger(self) -> None:
        with pytest.raises(
            ValueError,
            match="HEALTHY",
        ):
            ServiceRecoveryRule(
                action_id="restart-example-service",
                unit="example.service",
                enabled=True,
                trigger_statuses=(
                    HealthStatus.HEALTHY,
                ),
            )

    def test_rejects_duplicate_statuses(self) -> None:
        with pytest.raises(
            ValueError,
            match="unique",
        ):
            ServiceRecoveryRule(
                action_id="restart-example-service",
                unit="example.service",
                enabled=True,
                trigger_statuses=(
                    HealthStatus.CRITICAL,
                    HealthStatus.CRITICAL,
                ),
            )


class TestRecoveryConfig:
    """Test complete recovery configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = RecoveryConfig(
            execution=build_execution(),
            service_rules=(build_rule(),),
        )

        assert len(config.service_rules) == 1

    def test_rejects_duplicate_action_ids(self) -> None:
        with pytest.raises(
            ValueError,
            match="action IDs",
        ):
            RecoveryConfig(
                execution=build_execution(),
                service_rules=(
                    build_rule(unit="one.service"),
                    build_rule(unit="two.service"),
                ),
            )

    def test_rejects_duplicate_units(self) -> None:
        with pytest.raises(
            ValueError,
            match="service units",
        ):
            RecoveryConfig(
                execution=build_execution(),
                service_rules=(
                    build_rule(
                        action_id="restart-one",
                    ),
                    build_rule(
                        action_id="restart-two",
                    ),
                ),
            )
