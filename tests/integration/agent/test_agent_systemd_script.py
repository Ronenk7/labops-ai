"""Integration tests for Agent systemd management."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.integration

CASES = load_test_fixture(
    "agent/systemd_service_cases.json"
)

PROJECT_ROOT = (
    Path(__file__).resolve().parents[3]
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "manage_agent_systemd_user.sh"
)
PYTHON_BIN = (
    PROJECT_ROOT
    / ".venv"
    / "bin"
    / "python"
)
CONFIG_FILE = (
    PROJECT_ROOT
    / "config"
    / "host_agent.json"
)


def run_script(
    action: str,
    *,
    home: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the management script in isolation."""
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment.pop(
        "XDG_CONFIG_HOME",
        None,
    )

    return subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            action,
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_has_valid_bash_syntax() -> None:
    """Pass Bash syntax validation."""
    result = subprocess.run(
        [
            "bash",
            "-n",
            str(SCRIPT_PATH),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_render_outputs_complete_user_service(
    tmp_path: Path,
) -> None:
    """Render a complete portable user unit."""
    result = run_script(
        "render",
        home=tmp_path,
    )

    assert result.returncode == 0
    assert result.stderr == ""

    unit_content = result.stdout

    for token in CASES[
        "static_unit_tokens"
    ]:
        assert token in unit_content

    assert (
        f"WorkingDirectory={PROJECT_ROOT}"
        in unit_content
    )
    assert (
        'WorkingDirectory="'
        not in unit_content
    )

    expected_exec_start = (
        f"ExecStart={PYTHON_BIN} "
        f'{CASES["exec_arguments"]} '
        f"{CONFIG_FILE}"
    )

    assert expected_exec_start in unit_content
    assert 'ExecStart="' not in unit_content

    assert (
        unit_content.count(
            "[Service]"
        )
        == 1
    )
    assert (
        unit_content.count(
            "ExecStart="
        )
        == 1
    )


def test_render_does_not_install_service(
    tmp_path: Path,
) -> None:
    """Avoid filesystem side effects in render mode."""
    result = run_script(
        "render",
        home=tmp_path,
    )

    service_path = (
        tmp_path
        / ".config"
        / "systemd"
        / "user"
        / CASES["service_name"]
    )

    assert result.returncode == 0
    assert not service_path.exists()


def test_script_verifies_runtime_and_fresh_heartbeat() -> None:
    """Keep service and heartbeat verification safeguards."""
    script_content = SCRIPT_PATH.read_text(
        encoding="utf-8"
    )

    for token in CASES[
        "management_script_tokens"
    ]:
        assert token in script_content


def test_rejects_unknown_action(
    tmp_path: Path,
) -> None:
    """Reject unsupported management actions."""
    case = CASES["invalid_action"]

    result = run_script(
        case["value"],
        home=tmp_path,
    )

    assert result.returncode == (
        case["expected_exit_code"]
    )
    assert result.stdout == ""
    assert (
        case["expected_error"]
        in result.stderr
    )
