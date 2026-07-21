"""Unit tests for the remote host agent."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from labops_ai.agent import (
    HeartbeatDeliveryError,
    HostAgent,
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/host_agent_cases.json"
)
BASE_CONFIGURATION = CASES["base_configuration"]
METADATA = CASES["host_metadata"]
BASE_TIME = datetime.fromisoformat(
    METADATA["input"]["observed_at"]
)


class RecordingHeartbeatSender:
    """Record successful heartbeat deliveries."""

    def __init__(self) -> None:
        """Initialize an empty call list."""
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


class ControlledHeartbeatSender:
    """Fail a configured number of delivery attempts."""

    def __init__(
        self,
        failures_before_success: int,
        *,
        error_factory: Callable[
            [], Exception
        ] | None = None,
    ) -> None:
        """Initialize deterministic delivery behavior."""
        self.failures_before_success = (
            failures_before_success
        )
        self.error_factory = (
            error_factory
            if error_factory is not None
            else lambda: HeartbeatDeliveryError(
                "Central API is unavailable."
            )
        )
        self.attempts = 0

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Fail until the configured attempt count."""
        self.attempts += 1

        if (
            self.attempts
            <= self.failures_before_success
        ):
            raise self.error_factory()


def build_config(
    *,
    host_id_override: str | None = None,
    retry_overrides: (
        dict[str, Any] | None
    ) = None,
) -> HostAgentConfig:
    """Build agent configuration from fixture data."""
    retry_values = {
        **BASE_CONFIGURATION["retry"],
        **(retry_overrides or {}),
    }

    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            host_id_override=host_id_override,
        ),
        server=HostAgentServerConfig(
            **BASE_CONFIGURATION["server"]
        ),
        schedule=HostAgentScheduleConfig(
            **BASE_CONFIGURATION["schedule"]
        ),
        retry=HostAgentRetryConfig(
            **retry_values
        ),
    )


def build_agent(
    sender: object,
    *,
    config: HostAgentConfig | None = None,
    sleeper: Callable[
        [float], None
    ] = lambda seconds: None,
) -> HostAgent:
    """Build a deterministic Agent from fixture data."""
    metadata = METADATA["input"]

    return HostAgent(
        config=(
            config
            if config is not None
            else build_config()
        ),
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
            lambda: metadata["architecture"]
        ),
        agent_version=metadata["agent_version"],
        sleeper=sleeper,
    )


def test_builds_and_sends_one_heartbeat() -> None:
    """Collect, normalize and send host metadata."""
    sender = RecordingHeartbeatSender()
    agent = build_agent(sender)

    heartbeat = agent.run_once()
    expected = METADATA["expected"]

    assert heartbeat.host_id == expected["host_id"]
    assert heartbeat.host_name == (
        expected["host_name"]
    )
    assert heartbeat.address == (
        expected["address"]
    )
    assert heartbeat.operating_system == (
        expected["operating_system"]
    )
    assert heartbeat.architecture == (
        expected["architecture"]
    )
    assert heartbeat.agent_version == (
        expected["agent_version"]
    )
    assert heartbeat.observed_at == datetime.fromisoformat(
        expected["observed_at"]
    )

    assert sender.calls == [
        (
            (
                "http://127.0.0.1:8000"
                "/api/v1/hosts/heartbeat"
            ),
            heartbeat,
            5.0,
        )
    ]


def test_uses_configured_host_id_override() -> None:
    """Prefer an explicit host identifier override."""
    case = CASES["host_id_override"]
    sender = RecordingHeartbeatSender()

    agent = build_agent(
        sender,
        config=build_config(
            host_id_override=case["input"],
        ),
    )

    heartbeat = agent.run_once()

    assert heartbeat.host_id == case["expected"]
    assert heartbeat.host_name == (
        METADATA["expected"]["host_name"]
    )


def test_retries_temporary_delivery_failures() -> None:
    """Retry until heartbeat delivery succeeds."""
    case = CASES["retry_success"]
    sender = ControlledHeartbeatSender(
        case["failures_before_success"]
    )
    sleep_calls: list[float] = []

    heartbeat = build_agent(
        sender,
        sleeper=sleep_calls.append,
    ).run_once()

    assert heartbeat.host_id == (
        METADATA["expected"]["host_id"]
    )
    assert sender.attempts == (
        case["expected_attempts"]
    )
    assert sleep_calls == case["expected_sleeps"]


def test_raises_after_retry_budget_is_exhausted() -> None:
    """Raise the final delivery error after all attempts."""
    case = CASES["retry_exhaustion"]
    sender = ControlledHeartbeatSender(
        case["failures_before_success"]
    )
    sleep_calls: list[float] = []

    with pytest.raises(
        HeartbeatDeliveryError,
        match="Central API is unavailable",
    ):
        build_agent(
            sender,
            sleeper=sleep_calls.append,
        ).run_once()

    assert sender.attempts == (
        case["expected_attempts"]
    )
    assert sleep_calls == case["expected_sleeps"]


def test_caps_exponential_retry_backoff() -> None:
    """Never sleep beyond the configured maximum."""
    case = CASES["backoff_cap"]
    sender = ControlledHeartbeatSender(
        case["failures_before_success"]
    )
    sleep_calls: list[float] = []

    build_agent(
        sender,
        config=build_config(
            retry_overrides=case["retry"],
        ),
        sleeper=sleep_calls.append,
    ).run_once()

    assert sender.attempts == (
        case["expected_attempts"]
    )
    assert sleep_calls == case["expected_sleeps"]


def test_does_not_retry_unexpected_errors() -> None:
    """Retry only explicit delivery failures."""
    sender = ControlledHeartbeatSender(
        failures_before_success=1,
        error_factory=lambda: ValueError(
            "Invalid sender state."
        ),
    )
    sleep_calls: list[float] = []

    with pytest.raises(
        ValueError,
        match="Invalid sender state",
    ):
        build_agent(
            sender,
            sleeper=sleep_calls.append,
        ).run_once()

    assert sender.attempts == 1
    assert sleep_calls == []


def test_rejects_sender_without_send_method() -> None:
    """Require the sender protocol."""
    with pytest.raises(
        TypeError,
        match="callable send method",
    ):
        build_agent(object())


def test_rejects_non_callable_dependency() -> None:
    """Require callable metadata providers."""
    metadata = METADATA["input"]

    with pytest.raises(
        TypeError,
        match="host_name_provider must be callable",
    ):
        HostAgent(
            config=build_config(),
            sender=RecordingHeartbeatSender(),
            clock=lambda: BASE_TIME,
            host_name_provider=metadata["host_name"],
            address_provider=lambda: metadata["address"],
            operating_system_provider=(
                lambda: metadata[
                    "operating_system"
                ]
            ),
            architecture_provider=(
                lambda: metadata["architecture"]
            ),
            agent_version=metadata["agent_version"],
        )
