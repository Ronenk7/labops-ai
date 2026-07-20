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
from labops_ai.hosts import HostHeartbeat


HeartbeatExecutor = Callable[
    [HostAgentConfigLoader],
    HostHeartbeat,
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


def execute_once(
    config_loader: HostAgentConfigLoader,
) -> HostHeartbeat:
    """Build the production agent and run it once."""
    if not isinstance(
        config_loader,
        HostAgentConfigLoader,
    ):
        raise TypeError(
            "config_loader must be a "
            "HostAgentConfigLoader."
        )

    agent = build_default_agent(
        config_loader=config_loader
    )

    return run_agent_once(agent)


def run_cli(
    arguments: Sequence[str] | None = None,
    *,
    executor: HeartbeatExecutor = execute_once,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the host-agent command-line interface."""
    if not callable(executor):
        raise TypeError(
            "executor must be callable."
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
        heartbeat = executor(config_loader)

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

    print(
        "Heartbeat sent successfully: "
        f"host_id={heartbeat.host_id}, "
        f"address={heartbeat.address}, "
        "observed_at="
        f"{heartbeat.observed_at.isoformat()}",
        file=output_stream,
    )

    return 0


def main() -> None:
    """Run the host-agent CLI process."""
    raise SystemExit(
        run_cli()
    )
