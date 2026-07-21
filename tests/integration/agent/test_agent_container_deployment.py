"""Tests for the containerized second Host Agent."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.integration

PROJECT_ROOT = (
    Path(__file__).resolve().parents[3]
)
DOCKERFILE = (
    PROJECT_ROOT
    / "deploy"
    / "agent"
    / "Dockerfile"
)
COMPOSE_FILE = (
    PROJECT_ROOT
    / "compose.agent.yaml"
)
CONFIG_FILE = (
    PROJECT_ROOT
    / "config"
    / "host_agent_container.json"
)
DOCKERIGNORE_FILE = (
    PROJECT_ROOT
    / ".dockerignore"
)

CASES = load_test_fixture(
    "agent/container_deployment_cases.json"
)


def test_agent_dockerfile_is_hardened() -> None:
    """Build the Agent with a non-root runtime."""
    content = DOCKERFILE.read_text(
        encoding="utf-8"
    )

    for token in CASES["dockerfile_tokens"]:
        assert token in content

    assert "USER root" not in content
    assert "pip install -e" not in content


def test_agent_compose_service_is_hardened() -> None:
    """Configure a restricted continuous Agent."""
    content = COMPOSE_FILE.read_text(
        encoding="utf-8"
    )

    for token in CASES["compose_tokens"]:
        assert token in content

    assert "privileged: true" not in content
    assert "network_mode: host" not in content
    assert "ports:" not in content


def test_container_agent_configuration() -> None:
    """Connect through Docker Desktop host DNS."""
    configuration = json.loads(
        CONFIG_FILE.read_text(
            encoding="utf-8"
        )
    )
    expected = CASES["config"]

    assert configuration["identity"][
        "host_id_override"
    ] is None
    assert configuration["server"][
        "base_url"
    ] == expected["base_url"]
    assert configuration["server"][
        "heartbeat_path"
    ] == expected["heartbeat_path"]
    assert configuration["schedule"][
        "interval_seconds"
    ] == expected["interval_seconds"]


def test_docker_context_excludes_runtime_data() -> None:
    """Exclude local runtime and development data."""
    content = DOCKERIGNORE_FILE.read_text(
        encoding="utf-8"
    )

    for token in (
        ".git",
        ".venv",
        ".pytest_cache",
        "**/__pycache__",
        "runtime",
        "tests",
        "*.sqlite3",
    ):
        assert token in content
