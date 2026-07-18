"""Inspect Linux services through systemctl."""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass


from labops_ai.services.service_config import (
    ServiceTargetConfig,
    SystemctlCommandConfig,
)
from labops_ai.services.service_result import (
    ServiceCheckResult,
    ServiceCheckStatus,
    ServiceFailureReason,
)


Command = tuple[str, ...]
CommandResult = subprocess.CompletedProcess[str]
CommandRunner = Callable[[Command, float], CommandResult]


def run_systemctl_command(
    command: Command,
    timeout_seconds: float,
) -> CommandResult:
    """Run one systemctl command and capture its output."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


@dataclass(frozen=True, slots=True)
class SystemctlServiceChecker:
    """Check Linux service state using systemctl show."""

    command_config: SystemctlCommandConfig
    runner: CommandRunner = run_systemctl_command

    def __post_init__(self) -> None:
        """Validate injected configuration and dependencies."""
        if not isinstance(
            self.command_config,
            SystemctlCommandConfig,
        ):
            raise TypeError(
                "command_config must be a "
                "SystemctlCommandConfig instance."
            )

        if not callable(self.runner):
            raise TypeError("runner must be callable.")

    def check(
        self,
        target: ServiceTargetConfig,
    ) -> ServiceCheckResult:
        """Inspect one configured service and return its state."""
        if not isinstance(target, ServiceTargetConfig):
            raise TypeError(
                "target must be a ServiceTargetConfig instance."
            )

        command = self._build_command(target.service_name)

        try:
            completed_process = self.runner(
                command,
                self.command_config.timeout_seconds,
            )
        except FileNotFoundError as error:
            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.SYSTEMCTL_NOT_FOUND,
                error=error,
                fallback_message="systemctl executable was not found.",
            )
        except subprocess.TimeoutExpired as error:
            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.TIMEOUT,
                error=error,
                fallback_message="systemctl command timed out.",
            )
        except OSError as error:
            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.COMMAND_FAILED,
                error=error,
                fallback_message="systemctl command failed.",
            )
        except Exception as error:
            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.UNKNOWN_ERROR,
                error=error,
                fallback_message=(
                    "An unexpected service check error occurred."
                ),
            )

        return self._build_completed_result(
            target=target,
            completed_process=completed_process,
        )

    def _build_command(self, service_name: str) -> Command:
        """Build the configured systemctl show command."""
        return (
            self.command_config.executable,
            "show",
            service_name,
            "--no-page",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
        )

    def _build_completed_result(
        self,
        target: ServiceTargetConfig,
        completed_process: CommandResult,
    ) -> ServiceCheckResult:
        """Convert command output into a structured result."""
        try:
            properties = self._parse_properties(
                completed_process.stdout
            )
        except ValueError as error:
            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.INVALID_RESPONSE,
                error=error,
                fallback_message=(
                    "systemctl returned an invalid response."
                ),
            )

        load_state = properties["LoadState"]
        active_state = properties["ActiveState"]
        sub_state = properties["SubState"]

        if load_state == "not-found":
            error_message = (
                completed_process.stderr.strip()
                or "Service unit was not found."
            )

            return ServiceCheckResult(
                service_name=target.service_name,
                label=target.label,
                status=ServiceCheckStatus.NOT_FOUND,
                load_state=load_state,
                active_state=active_state,
                sub_state=sub_state,
                failure_reason=(
                    ServiceFailureReason.UNIT_NOT_FOUND
                ),
                error_message=error_message,
            )

        if completed_process.returncode != 0:
            error_message = (
                completed_process.stderr.strip()
                or "systemctl returned a non-zero exit code."
            )

            return self._build_check_error(
                target=target,
                reason=ServiceFailureReason.COMMAND_FAILED,
                error=RuntimeError(error_message),
                fallback_message=error_message,
            )

        status = self._classify_active_state(active_state)

        return ServiceCheckResult(
            service_name=target.service_name,
            label=target.label,
            status=status,
            load_state=load_state,
            active_state=active_state,
            sub_state=sub_state,
        )

    @staticmethod
    def _parse_properties(output: str) -> dict[str, str]:
        """Parse systemctl key-value output."""
        properties: dict[str, str] = {}

        for raw_line in output.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            key, separator, value = line.partition("=")

            if not separator or not key.strip():
                raise ValueError(
                    "systemctl output contains an invalid line."
                )

            normalized_value = value.strip()

            if not normalized_value:
                raise ValueError(
                    "systemctl output contains an empty value."
                )

            properties[key.strip()] = normalized_value

        required_properties = {
            "LoadState",
            "ActiveState",
            "SubState",
        }
        missing_properties = required_properties - set(properties)

        if missing_properties:
            formatted_properties = ", ".join(
                sorted(missing_properties)
            )
            raise ValueError(
                "systemctl output is missing required properties: "
                f"{formatted_properties}."
            )

        return properties

    @staticmethod
    def _classify_active_state(
        active_state: str,
    ) -> ServiceCheckStatus:
        """Convert a raw ActiveState into a normalized state."""
        if active_state == "active":
            return ServiceCheckStatus.ACTIVE

        if active_state == "inactive":
            return ServiceCheckStatus.INACTIVE

        if active_state == "failed":
            return ServiceCheckStatus.FAILED

        if active_state in {
            "activating",
            "deactivating",
            "reloading",
        }:
            return ServiceCheckStatus.TRANSITIONING

        return ServiceCheckStatus.UNKNOWN

    @staticmethod
    def _build_check_error(
        target: ServiceTargetConfig,
        reason: ServiceFailureReason,
        error: Exception,
        fallback_message: str,
    ) -> ServiceCheckResult:
        """Build a normalized command-error result."""
        error_message = str(error).strip() or fallback_message

        return ServiceCheckResult(
            service_name=target.service_name,
            label=target.label,
            status=ServiceCheckStatus.CHECK_ERROR,
            failure_reason=reason,
            error_message=error_message,
        )