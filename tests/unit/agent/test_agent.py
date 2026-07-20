"""Tests for the remote host agent."""
from __future__ import annotations

from datetime import datetime, timezone

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


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    20,
    18,
    0,
    tzinfo=timezone.utc,
)


class FakeHeartbeatSender:
    """Record heartbeat delivery attempts."""

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
        """Record one simulated delivery."""
        self.calls.append(
            (
                url,
                heartbeat,
                timeout_seconds,
            )
        )


class FailingHeartbeatSender:
    """Fail temporarily before successful delivery."""

    def __init__(
        self,
        failures_before_success: int,
    ) -> None:
        """Initialize deterministic failures."""
        self.failures_before_success = (
            failures_before_success
        )
        self.attempts = 0

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Fail until the configured attempt."""
        self.attempts += 1

        if (
            self.attempts
            <= self.failures_before_success
        ):
            raise HeartbeatDeliveryError(
                "Central API is unavailable."
            )


def build_config() -> HostAgentConfig:
    """Build deterministic agent configuration."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            host_id_override=None,
        ),
        server=HostAgentServerConfig(
            base_url="http://127.0.0.1:8000",
            heartbeat_path=(
                "/api/v1/hosts/heartbeat"
            ),
            request_timeout_seconds=5,
        ),
        schedule=HostAgentScheduleConfig(
            interval_seconds=15,
        ),
        retry=HostAgentRetryConfig(
            max_attempts=3,
            initial_backoff_seconds=1,
            max_backoff_seconds=5,
        ),
    )


def test_builds_and_sends_one_heartbeat() -> None:
    """Collect host metadata and send one heartbeat."""
    sender = FakeHeartbeatSender()

    agent = HostAgent(
        config=build_config(),
        sender=sender,
        clock=lambda: BASE_TIME,
        host_name_provider=lambda: "lab-node-01",
        address_provider=lambda: "10.0.0.10",
        operating_system_provider=(
            lambda: "Ubuntu 24.04"
        ),
        architecture_provider=lambda: "x86_64",
        agent_version="0.1.0",
    )

    heartbeat = agent.run_once()

    assert heartbeat.host_id == "lab-node-01"
    assert heartbeat.host_name == "lab-node-01"
    assert heartbeat.address == "10.0.0.10"
    assert (
        heartbeat.operating_system
        == "Ubuntu 24.04"
    )
    assert heartbeat.architecture == "x86_64"
    assert heartbeat.agent_version == "0.1.0"
    assert heartbeat.observed_at == BASE_TIME

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


def test_retries_failed_heartbeat_delivery() -> None:
    """Retry temporary delivery failures."""
    sender = FailingHeartbeatSender(
        failures_before_success=2
    )
    sleep_calls: list[float] = []

    agent = HostAgent(
        config=build_config(),
        sender=sender,
        clock=lambda: BASE_TIME,
        host_name_provider=lambda: "lab-node-01",
        address_provider=lambda: "10.0.0.10",
        operating_system_provider=(
            lambda: "Ubuntu 24.04"
        ),
        architecture_provider=lambda: "x86_64",
        agent_version="0.1.0",
        sleeper=sleep_calls.append,
    )

    heartbeat = agent.run_once()

    assert heartbeat.host_id == "lab-node-01"
    assert sender.attempts == 3
    assert sleep_calls == [1.0, 2.0]