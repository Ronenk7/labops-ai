"""Integration tests for the host-agent process entrypoint."""
from __future__ import annotations

import subprocess
import sys

import pytest

from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.integration

CASES = load_test_fixture(
    "agent/cli_cases.json"
)


def test_module_entrypoint_exposes_help() -> None:
    """Launch the Agent module through Python."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "labops_ai.agent",
            "--help",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    for expected_token in CASES["help_tokens"]:
        assert expected_token in result.stdout

    assert result.stderr == ""
