"""Integration tests for process-level Agent signals."""
from __future__ import annotations

import signal
import subprocess
import sys

import pytest


pytestmark = pytest.mark.integration


def test_process_exits_cleanly_after_sigterm() -> None:
    """Convert a real SIGTERM into graceful shutdown."""
    script = """
from labops_ai.agent import SignalShutdownController

with SignalShutdownController() as controller:
    print("READY", flush=True)

    while not controller.should_stop():
        controller.wait(60)

    print(controller.reason.value, flush=True)
"""

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert process.stdout is not None

        ready_line = (
            process.stdout.readline().strip()
        )

        assert ready_line == "READY"

        process.send_signal(signal.SIGTERM)

        remaining_stdout, stderr = (
            process.communicate(timeout=5)
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert process.returncode == 0
    assert remaining_stdout.strip() == (
        "TERMINATE"
    )
    assert stderr == ""
