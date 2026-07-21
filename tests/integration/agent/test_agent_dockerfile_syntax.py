"""Regression tests for Dockerfile command syntax."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = (
    PROJECT_ROOT
    / "deploy"
    / "agent"
    / "Dockerfile"
)


def read_json_instruction(
    content: str,
    instruction: str,
) -> list[str]:
    """Read one single-line JSON Docker instruction."""
    pattern = rf"^{instruction}\s+(\[.*\])$"
    match = re.search(
        pattern,
        content,
        flags=re.MULTILINE,
    )

    assert match is not None, (
        f"{instruction} must use valid "
        "single-line JSON syntax."
    )

    parsed = json.loads(match.group(1))

    assert isinstance(parsed, list)
    assert all(
        isinstance(value, str)
        for value in parsed
    )

    return parsed


def test_entrypoint_uses_valid_json_syntax() -> None:
    """Require an executable JSON ENTRYPOINT."""
    content = DOCKERFILE.read_text(
        encoding="utf-8"
    )

    assert read_json_instruction(
        content,
        "ENTRYPOINT",
    ) == [
        "python",
        "-m",
        "labops_ai.agent",
    ]


def test_command_uses_valid_json_syntax() -> None:
    """Require continuous Agent arguments."""
    content = DOCKERFILE.read_text(
        encoding="utf-8"
    )

    assert read_json_instruction(
        content,
        "CMD",
    ) == [
        "--continuous",
        "--config",
        "/etc/labops-ai/host_agent.json",
    ]
