"""Unit tests for the remote host-agent CLI."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from labops_ai.agent.cli import run_cli
from labops_ai.config.utils import (
    HOST_AGENT_CONFIG_PATH,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/cli_cases.json"
)
HEARTBEAT_CASE = CASES["heartbeat"]

ERROR_TYPES: dict[
    str,
    type[Exception],
] = {
    "OSError": OSError,
    "RuntimeError": RuntimeError,
    "TypeError": TypeError,
    "ValueError": ValueError,
}


def build_heartbeat() -> HostHeartbeat:
    """Build deterministic CLI output data."""
    return HostHeartbeat(
        host_id=HEARTBEAT_CASE["host_id"],
        host_name=HEARTBEAT_CASE["host_name"],
        address=HEARTBEAT_CASE["address"],
        operating_system=(
            HEARTBEAT_CASE["operating_system"]
        ),
        architecture=(
            HEARTBEAT_CASE["architecture"]
        ),
        agent_version=(
            HEARTBEAT_CASE["agent_version"]
        ),
        observed_at=datetime.fromisoformat(
            HEARTBEAT_CASE["observed_at"]
        ),
    )


def test_runs_one_heartbeat_with_default_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use the default configuration path."""
    observed_paths: list[Path] = []

    def executor(config_loader):
        observed_paths.append(
            config_loader.config_path
        )
        return build_heartbeat()

    exit_code = run_cli(
        ["--once"],
        executor=executor,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert observed_paths == [
        HOST_AGENT_CONFIG_PATH
    ]
    assert captured.out == (
        CASES["expected_success_output"]
    )
    assert captured.err == ""


def test_uses_custom_configuration_path(
    tmp_path: Path,
) -> None:
    """Pass a custom path to the loader."""
    config_path = (
        tmp_path / "custom_agent.json"
    )
    observed_paths: list[Path] = []

    def executor(config_loader):
        observed_paths.append(
            config_loader.config_path
        )
        return build_heartbeat()

    exit_code = run_cli(
        [
            "--once",
            "--config",
            str(config_path),
        ],
        executor=executor,
    )

    assert exit_code == 0
    assert observed_paths == [config_path]


@pytest.mark.parametrize(
    "case",
    CASES["runtime_failures"],
    ids=lambda case: case["id"],
)
def test_returns_failure_for_operational_error(
    case: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Convert supported runtime errors to exit code one."""
    error_type = ERROR_TYPES[
        case["error_type"]
    ]

    def failing_executor(config_loader):
        raise error_type(case["message"])

    exit_code = run_cli(
        ["--once"],
        executor=failing_executor,
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == (
        f'Host agent failed: {case["message"]}\n'
    )


def test_requires_execution_mode() -> None:
    """Require one explicit execution mode."""
    with pytest.raises(
        SystemExit,
    ) as error:
        run_cli(
            [],
            executor=lambda config_loader: (
                build_heartbeat()
            ),
        )

    assert error.value.code == 2


def test_rejects_non_callable_executor() -> None:
    """Require an executable CLI dependency."""
    with pytest.raises(
        TypeError,
        match="executor must be callable",
    ):
        run_cli(
            ["--once"],
            executor=object(),
        )
