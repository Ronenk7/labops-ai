"""Unit tests for host-agent runtime composition."""
from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

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
    resolve_agent_version,
    run_agent_once,
    utc_now,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

AGENT_CASES = load_test_fixture(
    "agent/host_agent_cases.json"
)
RUNNER_CASES = load_test_fixture(
    "agent/runner_cases.json"
)

CONFIGURATION = AGENT_CASES[
    "base_configuration"
]
METADATA = AGENT_CASES["host_metadata"]
BASE_TIME = datetime.fromisoformat(
    METADATA["input"]["observed_at"]
)


class FakeConfigLoader:
    """Return deterministic Agent configuration."""

    def __init__(
        self,
        config: HostAgentConfig,
    ) -> None:
        """Store the configuration."""
        self.config = config
        self.calls = 0

    def load(self) -> HostAgentConfig:
        """Return the configured object."""
        self.calls += 1
        return self.config


class InvalidConfigLoader:
    """Return an unsupported configuration value."""

    def load(self):
        """Return invalid loader output."""
        return {}


class RecordingSender:
    """Record delivered heartbeat data."""

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
    """Build runtime configuration from fixture data."""
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


def build_providers() -> LocalHostProviders:
    """Build local providers from fixture data."""
    metadata = METADATA["input"]

    return LocalHostProviders(
        host_name_reader=(
            lambda: metadata["host_name"]
        ),
        address_reader=(
            lambda: metadata["address"]
        ),
        os_release_reader=lambda: {
            "PRETTY_NAME": metadata[
                "operating_system"
            ],
        },
        platform_reader=lambda: "unused",
        architecture_reader=(
            lambda: metadata["architecture"]
        ),
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
        agent_version=(
            METADATA["input"]["agent_version"]
        ),
    )

    assert isinstance(agent, HostAgent)

    heartbeat = agent.run_once()
    expected = METADATA["expected"]

    assert loader.calls == 1
    assert heartbeat.host_id == expected["host_id"]
    assert heartbeat.host_name == (
        expected["host_name"]
    )
    assert heartbeat.address == expected["address"]
    assert heartbeat.operating_system == (
        expected["operating_system"]
    )
    assert heartbeat.architecture == (
        expected["architecture"]
    )
    assert heartbeat.agent_version == (
        expected["agent_version"]
    )
    assert heartbeat.observed_at == BASE_TIME

    assert sender.calls == [
        (
            (
                CONFIGURATION["server"]["base_url"]
                + CONFIGURATION["server"][
                    "heartbeat_path"
                ]
            ),
            heartbeat,
            float(
                CONFIGURATION["server"][
                    "request_timeout_seconds"
                ]
            ),
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
        agent_version=(
            METADATA["input"]["agent_version"]
        ),
    )

    heartbeat = run_agent_once(agent)

    assert heartbeat.host_id == (
        METADATA["expected"]["host_id"]
    )
    assert len(sender.calls) == 1


def test_utc_now_is_timezone_aware() -> None:
    """Return a timezone-aware UTC timestamp."""
    current_time = utc_now()

    assert current_time.tzinfo is not None
    assert current_time.utcoffset() is not None
    assert (
        current_time.utcoffset().total_seconds()
        == 0
    )


def test_resolves_installed_agent_version() -> None:
    """Normalize installed package metadata."""
    case = RUNNER_CASES[
        "version_resolution"
    ]

    with patch(
        "labops_ai.agent.runner.version",
        return_value=case["installed_value"],
    ):
        result = resolve_agent_version()

    assert result == case["expected_installed"]


def test_falls_back_to_development_version() -> None:
    """Use a development version without package metadata."""
    case = RUNNER_CASES[
        "version_resolution"
    ]

    with patch(
        "labops_ai.agent.runner.version",
        side_effect=PackageNotFoundError(
            "labops-ai"
        ),
    ):
        result = resolve_agent_version()

    assert result == case["expected_fallback"]


def test_rejects_empty_resolved_version() -> None:
    """Reject empty package version metadata."""
    case = RUNNER_CASES[
        "version_resolution"
    ]

    with patch(
        "labops_ai.agent.runner.version",
        return_value=case["empty_value"],
    ):
        with pytest.raises(
            RuntimeError,
            match="must not be empty",
        ):
            resolve_agent_version()


def test_rejects_loader_without_load_method() -> None:
    """Require the configuration loader contract."""
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


def test_rejects_invalid_providers() -> None:
    """Require the local provider implementation."""
    with pytest.raises(
        TypeError,
        match="LocalHostProviders instance",
    ):
        build_default_agent(
            config_loader=FakeConfigLoader(
                build_config()
            ),
            providers=object(),
        )


def test_rejects_invalid_supplied_agent() -> None:
    """Require HostAgent for direct execution."""
    with pytest.raises(
        TypeError,
        match="agent must be a HostAgent",
    ):
        run_agent_once(object())
