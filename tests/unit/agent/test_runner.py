"""Tests for host-agent runtime composition."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from labops_ai.agent import (
    HostAgent,
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
    LocalHostProviders,
    build_default_agent,
    run_agent_once,
    utc_now,
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


class FakeConfigLoader:
    """Return deterministic agent configuration."""

    def __init__(
        self,
        config: HostAgentConfig,
    ) -> None:
        """Initialize the fake loader."""
        self.config = config
        self.calls = 0

    def load(self) -> HostAgentConfig:
        """Return the configured object."""
        self.calls += 1
        return self.config


class InvalidConfigLoader:
    """Return an invalid configuration object."""

    def load(self):
        """Return an unsupported value."""
        return {}


class RecordingSender:
    """Record sent heartbeats."""

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


def build_config() -> HostAgentConfig:
    """Build deterministic runtime configuration."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            host_id_override="host-001",
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


def build_providers() -> LocalHostProviders:
    """Build deterministic local providers."""
    return LocalHostProviders(
        host_name_reader=lambda: "lab-node-01",
        address_reader=lambda: "10.0.0.10",
        os_release_reader=lambda: {
            "PRETTY_NAME": "Ubuntu 24.04 LTS",
        },
        platform_reader=lambda: "unused",
        architecture_reader=lambda: "x86_64",
    )


def test_builds_complete_runtime_agent() -> None:
    """Wire configuration, providers and sender."""
    loader = FakeConfigLoader(
        build_config()
    )
    sender = RecordingSender()

    agent = build_default_agent(
        config_loader=loader,
        providers=build_providers(),
        sender=sender,
        clock=lambda: BASE_TIME,
        sleeper=lambda seconds: None,
        agent_version="0.1.0",
    )

    assert isinstance(agent, HostAgent)

    heartbeat = agent.run_once()

    assert loader.calls == 1
    assert heartbeat.host_id == "host-001"
    assert heartbeat.host_name == "lab-node-01"
    assert heartbeat.address == "10.0.0.10"
    assert (
        heartbeat.operating_system
        == "Ubuntu 24.04 LTS"
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


def test_runs_one_supplied_agent_cycle() -> None:
    """Run exactly one heartbeat cycle."""
    sender = RecordingSender()

    agent = build_default_agent(
        config_loader=FakeConfigLoader(
            build_config()
        ),
        providers=build_providers(),
        sender=sender,
        clock=lambda: BASE_TIME,
        agent_version="0.1.0",
    )

    heartbeat = run_agent_once(agent)

    assert heartbeat.host_id == "host-001"
    assert len(sender.calls) == 1


def test_utc_now_is_timezone_aware() -> None:
    """Return a valid UTC timestamp."""
    current_time = utc_now()

    assert current_time.tzinfo is not None
    assert current_time.utcoffset() is not None
    assert current_time.utcoffset().total_seconds() == 0


def test_rejects_loader_without_load_method() -> None:
    """Require a configuration loader contract."""
    with pytest.raises(
        TypeError,
        match="callable load method",
    ):
        build_default_agent(
            config_loader=object(),
        )


def test_rejects_invalid_loaded_configuration() -> None:
    """Require validated configuration output."""
    with pytest.raises(
        TypeError,
        match="must return a HostAgentConfig",
    ):
        build_default_agent(
            config_loader=InvalidConfigLoader(),
        )


def test_rejects_invalid_supplied_agent() -> None:
    """Require HostAgent for direct execution."""
    with pytest.raises(
        TypeError,
        match="agent must be a HostAgent",
    ):
        run_agent_once(object())