"""Tests for host availability evaluation."""
from datetime import datetime, timedelta, timezone

import pytest

from labops_ai.hosts import (
    HostAvailability,
    HostAvailabilityPolicy,
    HostHeartbeat,
    HostRecord,
    HostStatusEvaluator,
)


pytestmark = pytest.mark.unit

NOW = datetime(
    2026,
    7,
    20,
    10,
    0,
    tzinfo=timezone.utc,
)


def build_host() -> HostRecord:
    """Build one deterministic registered host."""
    heartbeat = HostHeartbeat(
        host_id="host-kukner7",
        host_name="Kukner7",
        address="192.168.1.50",
        operating_system="Ubuntu 24.04",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=NOW,
    )

    return HostRecord.register(heartbeat)


def build_evaluator() -> HostStatusEvaluator:
    """Build an evaluator with known thresholds."""
    policy = HostAvailabilityPolicy(
        stale_after_seconds=30,
        offline_after_seconds=90,
    )

    return HostStatusEvaluator(policy)


def test_reports_online_before_stale_threshold() -> None:
    status = build_evaluator().evaluate(
        build_host(),
        evaluated_at=NOW + timedelta(seconds=29),
    )

    assert status is HostAvailability.ONLINE


def test_reports_stale_at_stale_threshold() -> None:
    status = build_evaluator().evaluate(
        build_host(),
        evaluated_at=NOW + timedelta(seconds=30),
    )

    assert status is HostAvailability.STALE


def test_reports_stale_before_offline_threshold() -> None:
    status = build_evaluator().evaluate(
        build_host(),
        evaluated_at=NOW + timedelta(seconds=89),
    )

    assert status is HostAvailability.STALE


def test_reports_offline_at_offline_threshold() -> None:
    status = build_evaluator().evaluate(
        build_host(),
        evaluated_at=NOW + timedelta(seconds=90),
    )

    assert status is HostAvailability.OFFLINE


def test_rejects_evaluation_before_last_heartbeat() -> None:
    with pytest.raises(
        ValueError,
        match="must not be earlier",
    ):
        build_evaluator().evaluate(
            build_host(),
            evaluated_at=NOW - timedelta(seconds=1),
        )


@pytest.mark.parametrize(
    (
        "stale_after_seconds",
        "offline_after_seconds",
        "expected_error",
    ),
    (
        (0, 90, "must be positive"),
        (30, 30, "must be greater"),
        (60, 30, "must be greater"),
    ),
)
def test_rejects_invalid_policy(
    stale_after_seconds: int,
    offline_after_seconds: int,
    expected_error: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        HostAvailabilityPolicy(
            stale_after_seconds=stale_after_seconds,
            offline_after_seconds=(
                offline_after_seconds
            ),
        )


def test_rejects_naive_evaluation_time() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        build_evaluator().evaluate(
            build_host(),
            evaluated_at=datetime(2026, 7, 20),
        )
