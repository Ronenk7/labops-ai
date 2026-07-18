"""Unit tests for human-readable network connectivity reports."""
from __future__ import annotations
from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.network.connectivity_config import NetworkReportConfig
from labops_ai.network.connectivity_monitor import NetworkConnectivitySummary
from labops_ai.network.connectivity_report import (
    build_network_report,
    print_network_report,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture("network/connectivity_report_cases.json")
REPORT_CASES = load_test_fixture(
    "network/connectivity_report_config_cases.json"
)
REPORT = NetworkReportConfig(**REPORT_CASES["valid_report"])


def build_result(case: dict[str, Any]) -> ConnectivityCheckResult:
    """Build one connectivity result from external test data."""
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


def build_summary(case: dict[str, Any]) -> NetworkConnectivitySummary:
    """Build a complete network summary from external test data."""
    dns_case = case["dns"]
    tcp_case = case["tcp"]

    return NetworkConnectivitySummary(
        dns_result=build_result(dns_case),
        dns_status=HealthStatus(dns_case["health_status"]),
        tcp_result=build_result(tcp_case),
        tcp_status=HealthStatus(tcp_case["health_status"]),
        overall_status=HealthStatus(case["overall_status"]),
    )


class TestBuildNetworkReport:
    """Test construction of network connectivity reports."""

    def test_builds_healthy_network_report(self) -> None:
        case = CASES["healthy_summary"]

        actual_report = build_network_report(
            summary=build_summary(case),
            report=REPORT,
        )

        assert actual_report == case["expected_report"]

    def test_builds_failed_network_report(self) -> None:
        case = CASES["failed_summary"]

        actual_report = build_network_report(
            summary=build_summary(case),
            report=REPORT,
        )

        assert actual_report == case["expected_report"]

    def test_rejects_invalid_summary(self) -> None:
        with pytest.raises(
            TypeError,
            match="summary must be a NetworkConnectivitySummary",
        ):
            build_network_report(
                summary=object(),
                report=REPORT,
            )

    def test_rejects_invalid_report_configuration(self) -> None:
        with pytest.raises(
            TypeError,
            match="report must be a NetworkReportConfig",
        ):
            build_network_report(
                summary=build_summary(CASES["healthy_summary"]),
                report=object(),
            )


class TestPrintNetworkReport:
    """Test printing of network connectivity reports."""

    def test_prints_complete_network_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        case = CASES["healthy_summary"]

        print_network_report(
            summary=build_summary(case),
            report=REPORT,
        )

        captured = capsys.readouterr()

        assert captured.out == f'{case["expected_report"]}\n'
        assert captured.err == ""