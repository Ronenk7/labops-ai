"""Unit tests for Linux systemctl service checks."""
from __future__ import annotations

import subprocess
from typing import Any

import pytest

from labops_ai.services import (
    ServiceCheckStatus,
    ServiceFailureReason,
    ServiceTargetConfig,
    SystemctlCommandConfig,
    SystemctlServiceChecker,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "services/systemctl_checker_cases.json"
)
TARGET = ServiceTargetConfig(**CASES["target"])
COMMAND = SystemctlCommandConfig(**CASES["command"])


def build_runner(
    case: dict[str, Any],
):
    """Build a fake command runner from external test data."""
    def runner(
        command: tuple[str, ...],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=case["returncode"],
            stdout=case["stdout"],
            stderr=case["stderr"],
        )

    return runner


class TestSystemctlServiceChecker:
    """Test conversion of systemctl responses into results."""

    @pytest.mark.parametrize(
        ("case_name", "expected_status"),
        [
            ("active", ServiceCheckStatus.ACTIVE),
            ("inactive", ServiceCheckStatus.INACTIVE),
            ("failed", ServiceCheckStatus.FAILED),
            (
                "transitioning",
                ServiceCheckStatus.TRANSITIONING,
            ),
        ],
    )
    def test_returns_expected_service_status(
        self,
        case_name: str,
        expected_status: ServiceCheckStatus,
    ) -> None:
        checker = SystemctlServiceChecker(
            command_config=COMMAND,
            runner=build_runner(CASES[case_name]),
        )

        result = checker.check(TARGET)

        assert result.status is expected_status
        assert result.service_name == TARGET.service_name
        assert result.load_state is not None
        assert result.active_state is not None
        assert result.sub_state is not None

    def test_returns_not_found_result(self) -> None:
        checker = SystemctlServiceChecker(
            command_config=COMMAND,
            runner=build_runner(CASES["not_found"]),
        )

        result = checker.check(TARGET)

        assert result.status is ServiceCheckStatus.NOT_FOUND
        assert (
            result.failure_reason
            is ServiceFailureReason.UNIT_NOT_FOUND
        )

    def test_rejects_invalid_systemctl_response(self) -> None:
        checker = SystemctlServiceChecker(
            command_config=COMMAND,
            runner=build_runner(CASES["invalid_response"]),
        )

        result = checker.check(TARGET)

        assert result.status is ServiceCheckStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is ServiceFailureReason.INVALID_RESPONSE
        )

    def test_returns_timeout_result(self) -> None:
        def timeout_runner(
            command: tuple[str, ...],
            timeout_seconds: float,
        ) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=timeout_seconds,
            )

        checker = SystemctlServiceChecker(
            command_config=COMMAND,
            runner=timeout_runner,
        )

        result = checker.check(TARGET)

        assert result.status is ServiceCheckStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is ServiceFailureReason.TIMEOUT
        )

    def test_returns_missing_executable_result(self) -> None:
        def missing_runner(
            command: tuple[str, ...],
            timeout_seconds: float,
        ) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError(command[0])

        checker = SystemctlServiceChecker(
            command_config=COMMAND,
            runner=missing_runner,
        )

        result = checker.check(TARGET)

        assert result.status is ServiceCheckStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is ServiceFailureReason.SYSTEMCTL_NOT_FOUND
        )