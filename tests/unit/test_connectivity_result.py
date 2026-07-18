"""Unit tests for structured network connectivity results."""
from typing import Any

import pytest

from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("connectivity_result_cases.json")


def build_result(case: dict[str, Any]) -> ConnectivityCheckResult:
    """Build a connectivity result from external fixture data."""
    failure_reason = case.get("failure_reason")

    return ConnectivityCheckResult(
        check_type=ConnectivityCheckType(case["check_type"]),
        status=ConnectivityCheckStatus(case["status"]),
        target=case["target"],
        latency_ms=case.get("latency_ms"),
        resolved_address=case.get("resolved_address"),
        failure_reason=(
            ConnectivityFailureReason(failure_reason)
            if failure_reason is not None
            else None
        ),
        error_message=case.get("error_message"),
    )


@pytest.mark.unit
class TestConnectivityCheckResult:
    """Verify connectivity result validation and normalization."""

    @pytest.mark.parametrize("case", CASES["valid_results"], ids=lambda case: case["id"])
    def test_accepts_valid_results(self, case: dict[str, Any]) -> None:
        """Verify that valid external result data creates a result object."""
        result = build_result(case)

        assert result.target == case["expected_target"]
        assert result.resolved_address == case["expected_resolved_address"]

        if case["latency_ms"] is not None:
            assert result.latency_ms == float(case["latency_ms"])

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_string_targets"],
        ids=lambda case: case["id"],
    )
    def test_rejects_empty_target_values(self, case: dict[str, Any]) -> None:
        """Verify that empty connectivity targets are rejected."""
        base_case = CASES["base_passed_result"]

        with pytest.raises(ValueError, match="target must not be empty"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(base_case["check_type"]),
                status=ConnectivityCheckStatus(base_case["status"]),
                target=case["value"],
                latency_ms=base_case["latency_ms"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_target_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_string_targets(self, case: dict[str, Any]) -> None:
        """Verify that connectivity targets accept only string values."""
        base_case = CASES["base_passed_result"]

        with pytest.raises(TypeError, match="target must be a string"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(base_case["check_type"]),
                status=ConnectivityCheckStatus(base_case["status"]),
                target=case["value"],
                latency_ms=base_case["latency_ms"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_latency_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_numeric_latency(self, case: dict[str, Any]) -> None:
        """Verify that latency accepts only numeric values."""
        base_case = CASES["base_passed_result"]

        with pytest.raises(TypeError, match="latency must be a numeric"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(base_case["check_type"]),
                status=ConnectivityCheckStatus(base_case["status"]),
                target=base_case["target"],
                latency_ms=case["value"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_latency_values"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_latency_values(self, case: dict[str, Any]) -> None:
        """Verify that negative and non-finite latency values are rejected."""
        base_case = CASES["base_passed_result"]
        latency_value = float(case["value"]) if isinstance(case["value"], str) else case["value"]

        with pytest.raises(ValueError):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(base_case["check_type"]),
                status=ConnectivityCheckStatus(base_case["status"]),
                target=base_case["target"],
                latency_ms=latency_value,
            )

    @pytest.mark.parametrize(
        "case",
        CASES["passed_results_with_failure_details"],
        ids=lambda case: case["id"],
    )
    def test_rejects_failure_details_in_passed_results(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that successful checks cannot contain failure details."""
        base_case = CASES["base_passed_result"]
        failure_reason = case["failure_reason"]

        with pytest.raises(ValueError, match="cannot contain failure details"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(base_case["check_type"]),
                status=ConnectivityCheckStatus(base_case["status"]),
                target=base_case["target"],
                latency_ms=base_case["latency_ms"],
                failure_reason=(
                    ConnectivityFailureReason(failure_reason)
                    if failure_reason is not None
                    else None
                ),
                error_message=case["error_message"],
            )

    def test_rejects_failed_result_without_failure_reason(self) -> None:
        """Verify that failed checks must contain a normalized reason."""
        case = CASES["base_failed_result"]

        with pytest.raises(ValueError, match="must contain a failure reason"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(case["check_type"]),
                status=ConnectivityCheckStatus(case["status"]),
                target=case["target"],
                error_message=case["error_message"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_optional_strings"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_optional_strings(self, case: dict[str, Any]) -> None:
        """Verify that populated optional strings contain usable text."""
        base_case = CASES["base_passed_result"]

        result_values = {
            "check_type": ConnectivityCheckType(base_case["check_type"]),
            "status": ConnectivityCheckStatus(base_case["status"]),
            "target": base_case["target"],
            "latency_ms": base_case["latency_ms"],
            case["field"]: case["value"],
        }

        expected_error = TypeError if not isinstance(case["value"], str) else ValueError

        with pytest.raises(expected_error):
            ConnectivityCheckResult(**result_values)

    def test_rejects_invalid_check_type(self) -> None:
        """Verify that check_type must contain the correct enum."""
        case = CASES["base_passed_result"]

        with pytest.raises(TypeError, match="ConnectivityCheckType"):
            ConnectivityCheckResult(
                check_type=case["check_type"],
                status=ConnectivityCheckStatus(case["status"]),
                target=case["target"],
                latency_ms=case["latency_ms"],
            )

    def test_rejects_invalid_status(self) -> None:
        """Verify that status must contain the correct enum."""
        case = CASES["base_passed_result"]

        with pytest.raises(TypeError, match="ConnectivityCheckStatus"):
            ConnectivityCheckResult(
                check_type=ConnectivityCheckType(case["check_type"]),
                status=case["status"],
                target=case["target"],
                latency_ms=case["latency_ms"],
            )