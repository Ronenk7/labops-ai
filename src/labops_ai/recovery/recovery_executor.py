"""Execute allowlisted systemd recovery commands safely."""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ServiceRestartOutcome(StrEnum):
    """Define normalized command execution outcomes."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True, slots=True)
class ServiceRestartResult:
    """Represent one systemctl restart result."""

    unit: str
    outcome: ServiceRestartOutcome
    details: str
    return_code: int | None = None


@dataclass(frozen=True, slots=True)
class SystemctlRecoveryExecutor:
    """Restart an explicit service without invoking a shell."""

    runner: Callable[..., Any] = subprocess.run

    def __post_init__(self) -> None:
        """Validate the command runner dependency."""
        if not callable(self.runner):
            raise TypeError("runner must be callable.")

    def restart(
        self,
        unit: str,
        *,
        timeout_seconds: float,
    ) -> ServiceRestartResult:
        """Run one bounded systemctl restart command."""
        command = (
            "systemctl",
            "restart",
            unit,
        )

        try:
            completed = self.runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ServiceRestartResult(
                unit=unit,
                outcome=(
                    ServiceRestartOutcome.TIMED_OUT
                ),
                details=(
                    "systemctl restart exceeded "
                    "the configured timeout."
                ),
            )
        except OSError as error:
            return ServiceRestartResult(
                unit=unit,
                outcome=ServiceRestartOutcome.FAILED,
                details=(
                    "systemctl restart could not be "
                    f"started: {error}"
                ),
            )

        return_code = getattr(
            completed,
            "returncode",
            None,
        )

        if not isinstance(return_code, int):
            raise TypeError(
                "Command runner must return an integer "
                "returncode."
            )

        stdout = str(
            getattr(completed, "stdout", "") or ""
        ).strip()
        stderr = str(
            getattr(completed, "stderr", "") or ""
        ).strip()

        if return_code == 0:
            return ServiceRestartResult(
                unit=unit,
                outcome=(
                    ServiceRestartOutcome.SUCCEEDED
                ),
                details=stdout or (
                    "systemctl restart completed "
                    "successfully."
                ),
                return_code=return_code,
            )

        return ServiceRestartResult(
            unit=unit,
            outcome=ServiceRestartOutcome.FAILED,
            details=stderr or stdout or (
                "systemctl restart returned "
                f"exit code {return_code}."
            ),
            return_code=return_code,
        )
