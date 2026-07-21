"""Continuous heartbeat scheduling for the host agent."""
from __future__ import annotations

import time
from collections.abc import Callable

from labops_ai.agent.agent import (
    HostAgent,
    Sleeper,
)


StopPredicate = Callable[[], bool]


def _never_stop() -> bool:
    """Keep the production scheduler running."""
    return False


def run_agent_forever(
    agent: HostAgent,
    *,
    sleeper: Sleeper = time.sleep,
    should_stop: StopPredicate = _never_stop,
) -> None:
    """Run heartbeat cycles at the configured interval."""
    if not isinstance(
        agent,
        HostAgent,
    ):
        raise TypeError(
            "agent must be a HostAgent."
        )

    if not callable(sleeper):
        raise TypeError(
            "sleeper must be callable."
        )

    if not callable(should_stop):
        raise TypeError(
            "should_stop must be callable."
        )

    interval_seconds = (
        agent.config.schedule.interval_seconds
    )

    while not should_stop():
        agent.run_once()

        if should_stop():
            return

        sleeper(interval_seconds)
