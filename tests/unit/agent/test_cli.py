"""Unit tests for the remote host-agent CLI."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from labops_ai.agent import (
    ShutdownReason,
)
from labops_ai.agent.cli import (
    execute_continuously,
    run_cli,
)
from labops_ai.agent.loader import (
    HostAgentConfigLoader,
)
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
    """Pass a custom path to the one-shot executor."""
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


def test_runs_continuously_with_custom_config(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dispatch continuous mode with a custom path."""
    config_path = (
        tmp_path / "continuous_agent.json"
    )
    observed_paths: list[Path] = []

    def continuous_executor(config_loader):
        observed_paths.append(
            config_loader.config_path
        )
        return None

    exit_code = run_cli(
        [
            "--continuous",
            "--config",
            str(config_path),
        ],
        continuous_executor=continuous_executor,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert observed_paths == [config_path]
    assert captured.out == (
        CASES[
            "expected_continuous_return_output"
        ]
    )
    assert captured.err == ""


@pytest.mark.parametrize(
    "case",
    CASES["runtime_failures"],
    ids=lambda case: case["id"],
)
def test_returns_failure_for_operational_error(
    case: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Convert one-shot runtime errors to exit code one."""
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


def test_returns_failure_for_continuous_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Convert continuous runtime failure to exit code one."""
    case = CASES["continuous_failure"]

    def failing_executor(config_loader):
        raise RuntimeError(case["message"])

    exit_code = run_cli(
        ["--continuous"],
        continuous_executor=failing_executor,
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == (
        CASES["expected_continuous_start_output"]
    )
    assert captured.err == (
        f'Host agent failed: {case["message"]}\n'
    )


def test_stops_after_keyboard_interrupt_fallback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Treat an unhandled Ctrl+C as graceful shutdown."""
    def interrupted_executor(config_loader):
        raise KeyboardInterrupt

    exit_code = run_cli(
        ["--continuous"],
        continuous_executor=(
            interrupted_executor
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        CASES["expected_interrupt_output"]
    )
    assert captured.err == ""


def test_reports_interrupt_shutdown_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report SIGINT as a user-requested stop."""
    exit_code = run_cli(
        ["--continuous"],
        continuous_executor=(
            lambda config_loader:
            ShutdownReason.INTERRUPT
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        CASES["expected_interrupt_output"]
    )
    assert captured.err == ""


def test_reports_terminate_shutdown_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report SIGTERM as a system-requested stop."""
    exit_code = run_cli(
        ["--continuous"],
        continuous_executor=(
            lambda config_loader:
            ShutdownReason.TERMINATE
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        CASES["expected_terminate_output"]
    )
    assert captured.err == ""


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


def test_rejects_conflicting_execution_modes() -> None:
    """Prevent simultaneous execution modes."""
    with pytest.raises(
        SystemExit,
    ) as error:
        run_cli(
            [
                "--once",
                "--continuous",
            ],
        )

    assert error.value.code == 2


def test_rejects_non_callable_executor() -> None:
    """Require an executable one-shot dependency."""
    with pytest.raises(
        TypeError,
        match="executor must be callable",
    ):
        run_cli(
            ["--once"],
            executor=object(),
        )


def test_rejects_non_callable_continuous_executor() -> None:
    """Require an executable continuous dependency."""
    with pytest.raises(
        TypeError,
        match=(
            "continuous_executor must be callable"
        ),
    ):
        run_cli(
            ["--continuous"],
            continuous_executor=object(),
        )


def test_continuous_executor_uses_signal_controller() -> None:
    """Connect production composition and shutdown control."""
    config_loader = HostAgentConfigLoader()
    built_agent = object()

    class FakeShutdownController:
        """Provide deterministic stop dependencies."""

        reason = ShutdownReason.TERMINATE

        def __enter__(self):
            return self

        def __exit__(
            self,
            exception_type,
            exception_value,
            traceback,
        ):
            return None

        def wait(self, seconds):
            return None

        def should_stop(self):
            return True

    with (
        patch(
            "labops_ai.agent.cli.build_default_agent",
            return_value=built_agent,
        ) as builder,
        patch(
            "labops_ai.agent.cli.SignalShutdownController",
            return_value=FakeShutdownController(),
        ),
        patch(
            "labops_ai.agent.cli.run_agent_forever",
        ) as scheduler,
    ):
        result = execute_continuously(
            config_loader
        )

    builder.assert_called_once_with(
        config_loader=config_loader
    )
    scheduler.assert_called_once_with(
        built_agent,
        sleeper=(
            scheduler.call_args.kwargs[
                "sleeper"
            ]
        ),
        should_stop=(
            scheduler.call_args.kwargs[
                "should_stop"
            ]
        ),
    )
    assert result is ShutdownReason.TERMINATE
