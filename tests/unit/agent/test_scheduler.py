"""Unit tests for continuous host-agent scheduling."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from labops_ai.agent import (
    HeartbeatDeliveryError,
    HostAgent,
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
    run_agent_forever,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

AGENT_CASES = load_test_fixture(
    "agent/host_agent_cases.json"
)
SCHEDULER_CASES = load_test_fixture(
    "agent/scheduler_cases.json"
)

CONFIGURATION = AGENT_CASES[
    "base_configuration"
]
METADATA = AGENT_CASES["host_metadata"]
BASE_TIME = datetime.fromisoformat(
    METADATA["input"]["observed_at"]
)


def ignore_sleep(seconds: float) -> None:
    """Ignore a simulated sleep call."""


class RecordingSender:
    """Record successful heartbeat deliveries."""

    def __init__(self) -> None:
        """Initialize an empty delivery list."""
        self.calls: list[
            tuple[str, HostHeartbeat, float]
        ] = []

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Record one heartbeat delivery."""
        self.calls.append(
            (
                url,
                heartbeat,
                timeout_seconds,
            )
        )


class AlwaysFailingSender:
    """Fail every heartbeat delivery attempt."""

    def __init__(
        self,
        message: str,
    ) -> None:
        """Store the simulated failure message."""
        self.message = message
        self.attempts = 0

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Raise a delivery error on every attempt."""
        self.attempts += 1

        raise HeartbeatDeliveryError(
            self.message
        )


def build_config() -> HostAgentConfig:
    """Build Agent configuration from fixture data."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            **CONFIGURATION["identity"]
        ),
        server=HostAgentServerConfig(
            **CONFIGURATION["server"]
        ),
        schedule=HostAgentScheduleConfig(
            **CONFIGURATION["schedule"]
        ),
        retry=HostAgentRetryConfig(
            **CONFIGURATION["retry"]
        ),
    )


def build_agent(
    sender: object,
    *,
    retry_sleeper: Callable[
        [float],
        None,
    ] = ignore_sleep,
) -> HostAgent:
    """Build a deterministic scheduled Agent."""
    metadata = METADATA["input"]

    return HostAgent(
        config=build_config(),
        sender=sender,
        clock=lambda: BASE_TIME,
        host_name_provider=(
            lambda: metadata["host_name"]
        ),
        address_provider=(
            lambda: metadata["address"]
        ),
        operating_system_provider=(
            lambda: metadata[
                "operating_system"
            ]
        ),
        architecture_provider=(
            lambda: metadata[
                "architecture"
            ]
        ),
        agent_version=(
            metadata["agent_version"]
        ),
        sleeper=retry_sleeper,
    )


def test_runs_cycles_until_stop_requested() -> None:
    """Run heartbeat cycles until stopping is requested."""
    case = SCHEDULER_CASES[
        "continuous_run"
    ]
    sender = RecordingSender()
    scheduler_sleep_calls: list[float] = []

    run_agent_forever(
        build_agent(sender),
        sleeper=scheduler_sleep_calls.append,
        should_stop=lambda: (
            len(sender.calls)
            >= case["cycle_count"]
        ),
    )

    assert len(sender.calls) == (
        case["cycle_count"]
    )
    assert scheduler_sleep_calls == (
        case["expected_scheduler_sleeps"]
    )


def test_stops_before_first_cycle() -> None:
    """Avoid sending when stopping is already requested."""
    case = SCHEDULER_CASES[
        "stop_before_first_cycle"
    ]
    sender = RecordingSender()
    scheduler_sleep_calls: list[float] = []

    run_agent_forever(
        build_agent(sender),
        sleeper=scheduler_sleep_calls.append,
        should_stop=lambda: True,
    )

    assert len(sender.calls) == (
        case["expected_send_count"]
    )
    assert scheduler_sleep_calls == (
        case["expected_scheduler_sleeps"]
    )


def test_propagates_delivery_failure_without_cycle_sleep() -> None:
    """Stop the loop when a heartbeat cycle fails."""
    case = SCHEDULER_CASES[
        "delivery_failure"
    ]
    sender = AlwaysFailingSender(
        case["message"]
    )
    retry_sleep_calls: list[float] = []
    scheduler_sleep_calls: list[float] = []

    with pytest.raises(
        HeartbeatDeliveryError,
        match=case["message"],
    ):
        run_agent_forever(
            build_agent(
                sender,
                retry_sleeper=(
                    retry_sleep_calls.append
                ),
            ),
            sleeper=(
                scheduler_sleep_calls.append
            ),
            should_stop=lambda: False,
        )

    assert sender.attempts == (
        case["expected_attempts"]
    )
    assert retry_sleep_calls == (
        case["expected_retry_sleeps"]
    )
    assert scheduler_sleep_calls == (
        case["expected_scheduler_sleeps"]
    )


def test_rejects_invalid_agent() -> None:
    """Require a real HostAgent instance."""
    with pytest.raises(
        TypeError,
        match="agent must be a HostAgent",
    ):
        run_agent_forever(object())


def test_rejects_non_callable_sleeper() -> None:
    """Require a callable scheduling sleeper."""
    with pytest.raises(
        TypeError,
        match="sleeper must be callable",
    ):
        run_agent_forever(
            build_agent(
                RecordingSender()
            ),
            sleeper=15,
        )


def test_rejects_non_callable_stop_predicate() -> None:
    """Require a callable stop condition."""
    with pytest.raises(
        TypeError,
        match="should_stop must be callable",
    ):
        run_agent_forever(
            build_agent(
                RecordingSender()
            ),
            should_stop=False,
        )
