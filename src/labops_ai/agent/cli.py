"""Command-line interface for the remote host agent."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from labops_ai.agent.loader import (
    HostAgentConfigLoader,
)
from labops_ai.agent.runner import (
    build_default_agent,
    run_agent_once,
)
from labops_ai.agent.scheduler import (
    run_agent_forever,
)
from labops_ai.agent.shutdown import (
    ShutdownReason,
    SignalShutdownController,
)
from labops_ai.hosts import HostHeartbeat


HeartbeatExecutor = Callable[
    [HostAgentConfigLoader],
    HostHeartbeat,
]
ContinuousExecutor = Callable[
    [HostAgentConfigLoader],
    ShutdownReason | None,
]


def create_parser() -> argparse.ArgumentParser:
    """Create the host-agent argument parser."""
    parser = argparse.ArgumentParser(
        prog="labops-agent",
        description=(
            "Send Linux host metadata to the "
            "LabOps AI central API."
        ),
    )

    mode_group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Send one heartbeat and exit.",
    )
    mode_group.add_argument(
        "--continuous",
        action="store_true",
        help=(
            "Send heartbeats continuously at the "
            "configured interval."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Use a custom host-agent JSON "
            "configuration file."
        ),
    )

    return parser


def _validate_config_loader(
    config_loader: HostAgentConfigLoader,
) -> None:
    """Require the production configuration loader."""
    if not isinstance(
        config_loader,
        HostAgentConfigLoader,
    ):
        raise TypeError(
            "config_loader must be a "
            "HostAgentConfigLoader."
        )


def execute_once(
    config_loader: HostAgentConfigLoader,
) -> HostHeartbeat:
    """Build the production agent and run it once."""
    _validate_config_loader(config_loader)

    agent = build_default_agent(
        config_loader=config_loader
    )

    return run_agent_once(agent)


def execute_continuously(
    config_loader: HostAgentConfigLoader,
) -> ShutdownReason | None:
    """Run until SIGINT or SIGTERM requests shutdown."""
    _validate_config_loader(config_loader)

    agent = build_default_agent(
        config_loader=config_loader
    )

    with SignalShutdownController() as shutdown:
        run_agent_forever(
            agent,
            sleeper=shutdown.wait,
            should_stop=shutdown.should_stop,
        )

        return shutdown.reason


def _print_continuous_stop_message(
    reason: ShutdownReason | None,
    *,
    output_stream: TextIO,
) -> None:
    """Print the continuous runtime exit reason."""
    if reason is ShutdownReason.INTERRUPT:
        message = "Host agent stopped by user."
    elif reason is ShutdownReason.TERMINATE:
        message = (
            "Host agent stopped after "
            "termination signal."
        )
    else:
        message = "Host agent stopped."

    print(
        message,
        file=output_stream,
    )


def run_cli(
    arguments: Sequence[str] | None = None,
    *,
    executor: HeartbeatExecutor = execute_once,
    continuous_executor: ContinuousExecutor = (
        execute_continuously
    ),
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the host-agent command-line interface."""
    if not callable(executor):
        raise TypeError(
            "executor must be callable."
        )

    if not callable(continuous_executor):
        raise TypeError(
            "continuous_executor must be callable."
        )

    output_stream = (
        stdout
        if stdout is not None
        else sys.stdout
    )
    error_stream = (
        stderr
        if stderr is not None
        else sys.stderr
    )

    parser = create_parser()
    parsed_arguments = parser.parse_args(
        arguments
    )

    config_loader = (
        HostAgentConfigLoader(
            parsed_arguments.config
        )
        if parsed_arguments.config is not None
        else HostAgentConfigLoader()
    )

    try:
        if parsed_arguments.once:
            heartbeat = executor(config_loader)

            print(
                "Heartbeat sent successfully: "
                f"host_id={heartbeat.host_id}, "
                f"address={heartbeat.address}, "
                "observed_at="
                f"{heartbeat.observed_at.isoformat()}",
                file=output_stream,
            )
        else:
            print(
                "Host agent started in continuous mode. "
                "Press Ctrl+C to stop.",
                file=output_stream,
            )

            shutdown_reason = (
                continuous_executor(
                    config_loader
                )
            )

            _print_continuous_stop_message(
                shutdown_reason,
                output_stream=output_stream,
            )

    except KeyboardInterrupt:
        print(
            "Host agent stopped by user.",
            file=output_stream,
        )
        return 0

    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"Host agent failed: {error}",
            file=error_stream,
        )
        return 1

    return 0


def main() -> None:
    """Run the host-agent CLI process."""
    raise SystemExit(
        run_cli()
    )
