"""Unit tests for remote host-agent configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.agent import (
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/host_agent_config_cases.json"
)


def build_config(
    configuration: dict[str, Any],
) -> HostAgentConfig:
    """Build complete agent configuration from test data."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            **configuration["identity"]
        ),
        server=HostAgentServerConfig(
            **configuration["server"]
        ),
        schedule=HostAgentScheduleConfig(
            **configuration["schedule"]
        ),
        retry=HostAgentRetryConfig(
            **configuration["retry"]
        ),
    )


def test_creates_complete_valid_configuration() -> None:
    """Create and normalize every configuration section."""
    case = CASES["valid_configuration"]

    config = build_config(case)

    assert config.identity.host_id_override == "host-001"
    assert config.server.base_url == (
        "https://central.example.test"
    )
    assert config.server.heartbeat_url == (
        "https://central.example.test"
        "/api/v1/hosts/heartbeat"
    )
    assert config.server.request_timeout_seconds == 7.5
    assert config.schedule.interval_seconds == 15.0
    assert config.retry.max_attempts == 3
    assert config.retry.initial_backoff_seconds == 1.0
    assert config.retry.max_backoff_seconds == 5.0


def test_rejects_invalid_server_scheme() -> None:
    """Allow only HTTP and HTTPS server URLs."""
    with pytest.raises(
        ValueError,
        match="http or https",
    ):
        HostAgentServerConfig(
            **CASES["invalid_server_scheme"]
        )


def test_rejects_relative_heartbeat_path() -> None:
    """Require an absolute heartbeat API path."""
    with pytest.raises(
        ValueError,
        match="start with",
    ):
        HostAgentServerConfig(
            **CASES["relative_heartbeat_path"]
        )


def test_rejects_non_positive_interval() -> None:
    """Require a positive heartbeat interval."""
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        HostAgentScheduleConfig(
            **CASES["non_positive_schedule"]
        )


def test_rejects_invalid_retry_backoff_order() -> None:
    """Require maximum backoff to cover initial backoff."""
    with pytest.raises(
        ValueError,
        match="greater than or equal",
    ):
        HostAgentRetryConfig(
            **CASES["invalid_retry_order"]
        )


def test_rejects_boolean_retry_attempts() -> None:
    """Do not accept bool as an integer attempt count."""
    with pytest.raises(
        TypeError,
        match="integer",
    ):
        HostAgentRetryConfig(
            **CASES["boolean_retry_attempts"]
        )


@pytest.mark.parametrize(
    "case",
    CASES["invalid_composition_fields"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_configuration_composition(
    case: dict[str, Any],
) -> None:
    """Require the correct model for every section."""
    valid = CASES["valid_configuration"]

    values: dict[str, object] = {
        "identity": HostAgentIdentityConfig(
            **valid["identity"]
        ),
        "server": HostAgentServerConfig(
            **valid["server"]
        ),
        "schedule": HostAgentScheduleConfig(
            **valid["schedule"]
        ),
        "retry": HostAgentRetryConfig(
            **valid["retry"]
        ),
    }

    values[case["field"]] = case["value"]

    with pytest.raises(TypeError):
        HostAgentConfig(**values)
