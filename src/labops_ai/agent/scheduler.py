"""Continuous scheduling for the full Host Agent."""
from __future__ import annotations

import time
from collections.abc import Callable

from labops_ai.agent.agent import (
    HostAgent,
    Sleeper,
)


StopPredicate = Callable[[], bool]
MonotonicClock = Callable[[], float]


def _never_stop() -> bool:
    """Keep the production scheduler running."""
    return False


def _run_heartbeat_only(
    agent: HostAgent,
    *,
    sleeper: Sleeper,
    should_stop: StopPredicate,
) -> None:
    """Preserve the heartbeat-only scheduler."""
    interval_seconds = (
        agent.config.schedule.interval_seconds
    )

    while not should_stop():
        agent.run_once()

        if should_stop():
            return

        sleeper(interval_seconds)


def _run_full_monitoring(
    agent: HostAgent,
    *,
    sleeper: Sleeper,
    should_stop: StopPredicate,
    monotonic: MonotonicClock,
) -> None:
    """Schedule independent heartbeat and run cycles."""
    heartbeat_interval = (
        agent.config.schedule.interval_seconds
    )
    monitoring_interval = (
        agent.config.schedule
        .monitoring_interval_seconds
    )

    started_at = monotonic()
    next_heartbeat_at = started_at
    next_monitoring_at = started_at

    while not should_stop():
        current_time = monotonic()

        if current_time >= next_heartbeat_at:
            agent.run_once()
            next_heartbeat_at = (
                monotonic()
                + heartbeat_interval
            )

        if should_stop():
            return

        current_time = monotonic()

        if current_time >= next_monitoring_at:
            agent.run_monitoring_once()
            next_monitoring_at = (
                monotonic()
                + monitoring_interval
            )

        if should_stop():
            return

        current_time = monotonic()
        next_action_at = min(
            next_heartbeat_at,
            next_monitoring_at,
        )
        sleep_seconds = max(
            0.0,
            next_action_at - current_time,
        )

        sleeper(sleep_seconds)


def run_agent_forever(
    agent: HostAgent,
    *,
    sleeper: Sleeper = time.sleep,
    should_stop: StopPredicate = _never_stop,
    monotonic: MonotonicClock = time.monotonic,
) -> None:
    """Run heartbeat and monitoring cycles until shutdown."""
    if not isinstance(
        agent,
        HostAgent,
    ):
        raise TypeError(
            "agent must be a HostAgent."
        )

    for dependency_name, dependency in (
        ("sleeper", sleeper),
        ("should_stop", should_stop),
        ("monotonic", monotonic),
    ):
        if not callable(dependency):
            raise TypeError(
                f"{dependency_name} must be callable."
            )

    if not agent.monitoring_enabled:
        _run_heartbeat_only(
            agent,
            sleeper=sleeper,
            should_stop=should_stop,
        )
        return

    _run_full_monitoring(
        agent,
        sleeper=sleeper,
        should_stop=should_stop,
        monotonic=monotonic,
    )
