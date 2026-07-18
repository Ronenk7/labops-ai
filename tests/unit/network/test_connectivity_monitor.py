"""Unit tests for network connectivity monitoring."""
from __future__ import annotations
from dataclasses import dataclass

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.network.connectivity_config import (
    ConnectionSettings,
    ConnectivityConfig,
    DnsTestConfig,
    LatencyThresholds,
    NetworkReportConfig,
    TcpTestConfig,
)
from labops_ai.network.connectivity_monitor import (
    NetworkConnectivityMonitor,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "network/connectivity_monitor_cases.json"
)
REPORT_CASES = load_test_fixture(
    "network/connectivity_report_config_cases.json"
)
BASE_CONFIG = CASES["base_config"]
VALID_REPORT = REPORT_CASES["valid_report"]


@dataclass
class StubChecker:
    """Return a predefined value when its check is executed."""

    result: object
    call_count: int = 0

    def check(self) -> object:
        """Return the configured stub result."""
        self.call_count += 1
        return self.result


def build_config() -> ConnectivityConfig:
    """Build a valid connectivity configuration from test data."""
    return ConnectivityConfig(
        dns_test=DnsTestConfig(
            hostname=BASE_CONFIG["dns_hostname"],
        ),
        tcp_test=TcpTestConfig(
            host=BASE_CONFIG["tcp_host"],
            port=BASE_CONFIG["tcp_port"],
        ),
        connection=ConnectionSettings(
            timeout_seconds=BASE_CONFIG["timeout_seconds"],
        ),
        latency_thresholds_ms=LatencyThresholds(
            warning=BASE_CONFIG["warning_latency_ms"],
            critical=BASE_CONFIG["critical_latency_ms"],
        ),
        report=NetworkReportConfig(**VALID_REPORT),
    )


def build_passed_result(
    check_type: ConnectivityCheckType,
    latency_ms: float | None,
) -> ConnectivityCheckResult:
    """Build a passed connectivity result for monitor tests."""
    target = (
        BASE_CONFIG["dns_hostname"]
        if check_type is ConnectivityCheckType.DNS
        else (
            f'{BASE_CONFIG["tcp_host"]}:'
            f'{BASE_CONFIG["tcp_port"]}'
        )
    )

    return ConnectivityCheckResult(
        check_type=check_type,
        status=ConnectivityCheckStatus.PASSED,
        target=target,
        latency_ms=latency_ms,
    )


class TestNetworkConnectivityMonitor:
    """Test combined DNS and TCP monitoring behavior."""

    def test_runs_dns_and_tcp_checks_and_returns_summary(
        self,
    ) -> None:
        dns_result = build_passed_result(
            ConnectivityCheckType.DNS,
            10.0,
        )
        tcp_result = build_passed_result(
            ConnectivityCheckType.TCP,
            20.0,
        )
        dns_checker = StubChecker(dns_result)
        tcp_checker = StubChecker(tcp_result)

        summary = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=dns_checker,
            tcp_checker=tcp_checker,
        ).run()

        assert summary.dns_result is dns_result
        assert summary.dns_status is HealthStatus.HEALTHY
        assert summary.tcp_result is tcp_result
        assert summary.tcp_status is HealthStatus.HEALTHY
        assert summary.overall_status is HealthStatus.HEALTHY
        assert dns_checker.call_count == 1
        assert tcp_checker.call_count == 1

    @pytest.mark.parametrize(
        ("latency_ms", "expected_status"),
        [
            (
                case["latency_ms"],
                HealthStatus(case["expected_status"]),
            )
            for case in CASES["latency_evaluation_cases"]
        ],
        ids=[
            case["id"]
            for case in CASES["latency_evaluation_cases"]
        ],
    )
    def test_evaluates_latency_using_external_thresholds(
        self,
        latency_ms: float,
        expected_status: HealthStatus,
    ) -> None:
        monitor = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.DNS,
                    latency_ms,
                )
            ),
            tcp_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    latency_ms,
                )
            ),
        )

        result = build_passed_result(
            ConnectivityCheckType.DNS,
            latency_ms,
        )

        assert monitor.evaluate_result(result) is expected_status

    def test_classifies_failed_check_as_critical(self) -> None:
        result = ConnectivityCheckResult(
            check_type=ConnectivityCheckType.DNS,
            status=ConnectivityCheckStatus.FAILED,
            target=BASE_CONFIG["dns_hostname"],
            failure_reason=(
                ConnectivityFailureReason.DNS_RESOLUTION_FAILED
            ),
            error_message="DNS resolution failed.",
        )
        monitor = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=StubChecker(result),
            tcp_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    20.0,
                )
            ),
        )

        assert (
            monitor.evaluate_result(result)
            is HealthStatus.CRITICAL
        )

    def test_rejects_passed_result_without_latency(self) -> None:
        result = build_passed_result(
            ConnectivityCheckType.DNS,
            None,
        )
        monitor = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=StubChecker(result),
            tcp_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    20.0,
                )
            ),
        )

        with pytest.raises(
            ValueError,
            match="passed connectivity result must contain latency",
        ):
            monitor.evaluate_result(result)

    def test_rejects_checker_returning_wrong_result_type(
        self,
    ) -> None:
        monitor = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=StubChecker(object()),
            tcp_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    20.0,
                )
            ),
        )

        with pytest.raises(
            TypeError,
            match="must return ConnectivityCheckResult",
        ):
            monitor.run()

    def test_rejects_dns_checker_returning_tcp_result(
        self,
    ) -> None:
        monitor = NetworkConnectivityMonitor(
            config=build_config(),
            dns_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    20.0,
                )
            ),
            tcp_checker=StubChecker(
                build_passed_result(
                    ConnectivityCheckType.TCP,
                    20.0,
                )
            ),
        )

        with pytest.raises(ValueError, match="Expected DNS result"):
            monitor.run()

    def test_rejects_invalid_checker_dependency(self) -> None:
        with pytest.raises(
            TypeError,
            match=(
                "dns_checker must provide "
                "a callable check method"
            ),
        ):
            NetworkConnectivityMonitor(
                config=build_config(),
                dns_checker=object(),
                tcp_checker=StubChecker(
                    build_passed_result(
                        ConnectivityCheckType.TCP,
                        20.0,
                    )
                ),
            )


class TestOverallNetworkStatus:
    """Test network-wide status aggregation."""

    @pytest.mark.parametrize(
        ("statuses", "expected_status"),
        [
            (
                tuple(
                    HealthStatus(value)
                    for value in case["statuses"]
                ),
                HealthStatus(case["expected_status"]),
            )
            for case in CASES["overall_status_cases"]
        ],
        ids=[
            case["id"]
            for case in CASES["overall_status_cases"]
        ],
    )
    def test_returns_highest_network_severity(
        self,
        statuses: tuple[HealthStatus, ...],
        expected_status: HealthStatus,
    ) -> None:
        actual_status = (
            NetworkConnectivityMonitor.get_overall_status(
                *statuses
            )
        )

        assert actual_status is expected_status

    def test_rejects_empty_status_collection(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one health status",
        ):
            NetworkConnectivityMonitor.get_overall_status()