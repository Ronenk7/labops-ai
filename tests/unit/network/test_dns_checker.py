"""Unit tests for DNS connectivity checking."""
import socket
from typing import Any
from unittest.mock import Mock, patch

import pytest

from labops_ai.network.connectivity_config import DnsTestConfig
from labops_ai.network.connectivity_result import (
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.network.dns_checker import DnsConnectivityChecker, resolve_hostname
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("network/dns_checker_cases.json")


@pytest.mark.unit
class TestDnsConnectivityChecker:
    """Verify DNS connectivity result generation."""

    @pytest.mark.parametrize(
        "case",
        CASES["successful_checks"],
        ids=lambda case: case["id"],
    )
    def test_returns_passed_result_after_successful_resolution(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify successful resolution, latency, and resolved address."""
        resolver = Mock(return_value=case["resolved_address"])
        clock = Mock(side_effect=case["clock_values"])
        config = DnsTestConfig(hostname=case["hostname"])

        result = DnsConnectivityChecker(
            config=config,
            resolver=resolver,
            clock=clock,
        ).check()

        assert result.check_type is ConnectivityCheckType.DNS
        assert result.status is ConnectivityCheckStatus.PASSED
        assert result.target == case["hostname"]
        assert result.resolved_address == case["resolved_address"]
        assert result.latency_ms == pytest.approx(case["expected_latency_ms"])
        assert result.failure_reason is None
        assert result.error_message is None
        resolver.assert_called_once_with(case["hostname"])

    @pytest.mark.parametrize(
        "case",
        CASES["dns_resolution_failures"],
        ids=lambda case: case["id"],
    )
    def test_returns_dns_failure_result(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of DNS resolution failures."""
        resolver = Mock(side_effect=socket.gaierror(case["error_message"]))
        config = DnsTestConfig(hostname=case["hostname"])

        result = DnsConnectivityChecker(
            config=config,
            resolver=resolver,
        ).check()

        assert result.status is ConnectivityCheckStatus.FAILED
        assert result.failure_reason is ConnectivityFailureReason(
            case["expected_reason"]
        )
        assert result.error_message == case["error_message"]
        assert result.latency_ms is None

    @pytest.mark.parametrize(
        "case",
        CASES["timeout_failures"],
        ids=lambda case: case["id"],
    )
    def test_returns_timeout_result(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of DNS timeout failures."""
        resolver = Mock(side_effect=TimeoutError(case["error_message"]))
        config = DnsTestConfig(hostname=case["hostname"])

        result = DnsConnectivityChecker(
            config=config,
            resolver=resolver,
        ).check()

        assert result.status is ConnectivityCheckStatus.FAILED
        assert result.failure_reason is ConnectivityFailureReason(
            case["expected_reason"]
        )
        assert result.error_message == case["error_message"]

    @pytest.mark.parametrize(
        "case",
        CASES["operating_system_failures"],
        ids=lambda case: case["id"],
    )
    def test_returns_unknown_error_result(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of other operating-system failures."""
        resolver = Mock(side_effect=OSError(case["error_message"]))
        config = DnsTestConfig(hostname=case["hostname"])

        result = DnsConnectivityChecker(
            config=config,
            resolver=resolver,
        ).check()

        assert result.status is ConnectivityCheckStatus.FAILED
        assert result.failure_reason is ConnectivityFailureReason(
            case["expected_reason"]
        )
        assert result.error_message == case["error_message"]


@pytest.mark.unit
class TestResolveHostname:
    """Verify the operating-system DNS resolver adapter."""

    def test_returns_first_resolved_address(self) -> None:
        """Verify extraction of the first address returned by getaddrinfo."""
        case = CASES["resolver_adapter"]

        address_info = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (case["resolved_address"], 0),
            )
        ]

        with patch(
            "labops_ai.network.dns_checker.socket.getaddrinfo",
            return_value=address_info,
        ) as resolver_mock:
            result = resolve_hostname(case["hostname"])

        assert result == case["resolved_address"]

        resolver_mock.assert_called_once_with(
            case["hostname"],
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

    def test_rejects_empty_resolver_response(self) -> None:
        """Verify that an empty operating-system response is treated as failure."""
        case = CASES["resolver_adapter"]

        with patch(
            "labops_ai.network.dns_checker.socket.getaddrinfo",
            return_value=[],
        ):
            with pytest.raises(socket.gaierror, match="No IP address"):
                resolve_hostname(case["hostname"])