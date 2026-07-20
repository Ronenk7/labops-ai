"""Tests for remote host-agent configuration."""
from __future__ import annotations

import json

import pytest

from labops_ai.agent import (
    HostAgentConfigLoader,
    HostAgentRetryConfig,
    HostAgentServerConfig,
)


pytestmark = pytest.mark.unit


def test_loads_default_agent_configuration() -> None:
    """Load the production JSON configuration."""
    config = HostAgentConfigLoader().load()

    assert config.server.heartbeat_url == (
        "http://127.0.0.1:8000"
        "/api/v1/hosts/heartbeat"
    )
    assert (
        config.schedule.interval_seconds
        == 15
    )
    assert config.retry.max_attempts == 3


def test_rejects_unsupported_top_level_key(
    tmp_path,
) -> None:
    """Reject unknown configuration sections."""
    path = tmp_path / "agent.json"

    payload = {
        "identity": {
            "host_id_override": None,
        },
        "server": {
            "base_url": (
                "http://127.0.0.1:8000"
            ),
            "heartbeat_path": "/heartbeat",
            "request_timeout_seconds": 5,
        },
        "schedule": {
            "interval_seconds": 15,
        },
        "retry": {
            "max_attempts": 3,
            "initial_backoff_seconds": 1,
            "max_backoff_seconds": 5,
        },
        "unexpected": {},
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported keys",
    ):
        HostAgentConfigLoader(path).load()


def test_rejects_invalid_server_scheme() -> None:
    """Allow only HTTP and HTTPS URLs."""
    with pytest.raises(
        ValueError,
        match="http or https",
    ):
        HostAgentServerConfig(
            base_url="ftp://example.test",
            heartbeat_path="/heartbeat",
            request_timeout_seconds=5,
        )


def test_rejects_heartbeat_path_without_slash() -> None:
    """Require an absolute API path."""
    with pytest.raises(
        ValueError,
        match="start with",
    ):
        HostAgentServerConfig(
            base_url="https://example.test",
            heartbeat_path="heartbeat",
            request_timeout_seconds=5,
        )


def test_rejects_invalid_retry_backoff_order() -> None:
    """Require maximum backoff to cover initial."""
    with pytest.raises(
        ValueError,
        match="greater than or equal",
    ):
        HostAgentRetryConfig(
            max_attempts=3,
            initial_backoff_seconds=10,
            max_backoff_seconds=5,
        )


def test_rejects_boolean_retry_attempts() -> None:
    """Do not accept bool as an integer count."""
    with pytest.raises(
        TypeError,
        match="integer",
    ):
        HostAgentRetryConfig(
            max_attempts=True,
            initial_backoff_seconds=1,
            max_backoff_seconds=5,
        )
