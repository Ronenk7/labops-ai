"""Integration tests for host-agent JSON configuration loading."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from labops_ai.agent import (
    HostAgentConfig,
    HostAgentConfigLoader,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.integration

CASES = load_test_fixture(
    "config/host_agent_loader_cases.json"
)


def write_config(
    tmp_path: Path,
    configuration: dict[str, Any],
) -> Path:
    """Write one temporary host-agent JSON file."""
    config_path = tmp_path / "host_agent.json"

    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )

    return config_path


def test_loads_default_project_configuration() -> None:
    """Verify that the production JSON is valid."""
    config = HostAgentConfigLoader().load()

    assert isinstance(config, HostAgentConfig)
    assert config.server.heartbeat_url.endswith(
        "/api/v1/hosts/heartbeat"
    )
    assert config.server.request_timeout_seconds > 0
    assert config.schedule.interval_seconds > 0
    assert config.retry.max_attempts >= 1
    assert (
        config.retry.max_backoff_seconds
        >= config.retry.initial_backoff_seconds
    )


def test_loads_custom_configuration(
    tmp_path: Path,
) -> None:
    """Convert a custom JSON file into models."""
    case = CASES["valid_custom_configuration"]
    config_path = write_config(tmp_path, case)

    config = HostAgentConfigLoader(
        config_path
    ).load()

    assert config.identity.host_id_override == (
        case["identity"]["host_id_override"]
    )
    assert config.server.base_url == (
        case["server"]["base_url"]
    )
    assert config.server.heartbeat_path == (
        case["server"]["heartbeat_path"]
    )
    assert config.schedule.interval_seconds == float(
        case["schedule"]["interval_seconds"]
    )
    assert config.retry.max_attempts == (
        case["retry"]["max_attempts"]
    )


def test_rejects_missing_section(
    tmp_path: Path,
) -> None:
    """Reject an incomplete top-level configuration."""
    config_path = write_config(
        tmp_path,
        CASES["missing_section_configuration"],
    )

    with pytest.raises(
        ValueError,
        match="Missing required keys",
    ):
        HostAgentConfigLoader(config_path).load()


def test_rejects_unsupported_top_level_key(
    tmp_path: Path,
) -> None:
    """Reject unknown configuration sections."""
    config_path = write_config(
        tmp_path,
        CASES[
            "unsupported_top_level_key_configuration"
        ],
    )

    with pytest.raises(
        ValueError,
        match="Unsupported keys",
    ):
        HostAgentConfigLoader(config_path).load()


def test_rejects_invalid_section_type(
    tmp_path: Path,
) -> None:
    """Require every section to be a JSON object."""
    config_path = write_config(
        tmp_path,
        CASES[
            "invalid_section_type_configuration"
        ],
    )

    with pytest.raises(
        ValueError,
        match="must be a JSON object",
    ):
        HostAgentConfigLoader(config_path).load()
