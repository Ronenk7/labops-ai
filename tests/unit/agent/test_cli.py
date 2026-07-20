"""Tests for the remote host-agent CLI."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from labops_ai.agent.cli import run_cli
from labops_ai.config.utils import (
    HOST_AGENT_CONFIG_PATH,
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


def build_heartbeat() -> HostHeartbeat:
    """Build deterministic CLI output data."""
    return HostHeartbeat(
        host_id="host-001",
        host_name="lab-node-01",
        address="10.0.0.10",
        operating_system="Ubuntu 24.04 LTS",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=BASE_TIME,
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
    assert (
        "Heartbeat sent successfully"
        in captured.out
    )
    assert "host_id=host-001" in captured.out
    assert "address=10.0.0.10" in captured.out
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


def test_returns_failure_for_runtime_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report an operational agent failure."""
    def failing_executor(config_loader):
        raise RuntimeError(
            "central API unavailable"
        )

    exit_code = run_cli(
        ["--once"],
        executor=failing_executor,
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == (
        "Host agent failed: "
        "central API unavailable\n"
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


def test_module_entrypoint_exposes_help() -> None:
    """Run the package through Python module mode."""
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

    assert "usage: labops-agent" in result.stdout
    assert "--once" in result.stdout
    assert "--config" in result.stdout
