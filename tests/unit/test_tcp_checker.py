"""Unit tests for TCP connectivity checking."""
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from labops_ai.network.connectivity_config import ConnectionSettings, TcpTestConfig
from labops_ai.network.connectivity_result import (
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.network.tcp_checker import (
    TcpConnectivityChecker,
    connect_to_tcp_target,
)
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("tcp_checker_cases.json")

CONNECTION_EXCEPTION_TYPES = {
    "ConnectionRefusedError": ConnectionRefusedError,
    "OSError": OSError,
}


def build_checker(
    case: dict[str, Any],
    connector: Mock,
    clock: Mock | None = None,
) -> TcpConnectivityChecker:
    """Build a TCP checker from external fixture data."""
    return TcpConnectivityChecker(
        tcp_config=TcpTestConfig(
            host=case["host"],
            port=case["port"],
        ),
        connection_settings=ConnectionSettings(
            timeout_seconds=case["timeout_seconds"],
        ),
        connector=connector,
        clock=clock if clock is not None else Mock(return_value=0.0),
    )


@pytest.mark.unit
class TestTcpConnectivityChecker:
    """Verify TCP connectivity result generation."""

    @pytest.mark.parametrize(
        "case",
        CASES["successful_checks"],
        ids=lambda case: case["id"],
    )
    def test_returns_passed_result_after_successful_connection(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify successful connection, latency, and target formatting."""
        connector = Mock()
        clock = Mock(side_effect=case["clock_values"])
        checker = build_checker(case, connector, clock)

        result = checker.check()

        assert result.check_type is ConnectivityCheckType.TCP
        assert result.status is ConnectivityCheckStatus.PASSED
        assert result.target == case["expected_target"]
        assert result.latency_ms == pytest.approx(case["expected_latency_ms"])
        assert result.resolved_address is None
        assert result.failure_reason is None
        assert result.error_message is None

        connector.assert_called_once_with(
            case["host"],
            case["port"],
            case["timeout_seconds"],
        )

    @pytest.mark.parametrize(
        "case",
        CASES["connection_failures"],
        ids=lambda case: case["id"],
    )
    def test_returns_tcp_connection_failure(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of operating-system connection failures."""
        exception_type = CONNECTION_EXCEPTION_TYPES[case["exception_type"]]
        connector = Mock(side_effect=exception_type(case["error_message"]))
        checker = build_checker(case, connector)

        result = checker.check()

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
    def test_returns_timeout_failure(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of TCP timeout failures."""
        connector = Mock(side_effect=TimeoutError(case["error_message"]))
        checker = build_checker(case, connector)

        result = checker.check()

        assert result.status is ConnectivityCheckStatus.FAILED
        assert result.failure_reason is ConnectivityFailureReason(
            case["expected_reason"]
        )
        assert result.error_message == case["error_message"]

    @pytest.mark.parametrize(
        "case",
        CASES["unknown_failures"],
        ids=lambda case: case["id"],
    )
    def test_returns_unknown_failure(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify normalization of unexpected connector failures."""
        connector = Mock(side_effect=RuntimeError(case["error_message"]))
        checker = build_checker(case, connector)

        result = checker.check()

        assert result.status is ConnectivityCheckStatus.FAILED
        assert result.failure_reason is ConnectivityFailureReason(
            case["expected_reason"]
        )
        assert result.error_message == case["error_message"]

    def test_rejects_invalid_tcp_config(self) -> None:
        """Verify that the checker requires a TcpTestConfig object."""
        case = CASES["adapter"]

        with pytest.raises(TypeError, match="TcpTestConfig"):
            TcpConnectivityChecker(
                tcp_config=CASES["invalid_dependencies"]["tcp_config"],
                connection_settings=ConnectionSettings(
                    timeout_seconds=case["timeout_seconds"]
                ),
            )

    def test_rejects_invalid_connection_settings(self) -> None:
        """Verify that the checker requires ConnectionSettings."""
        case = CASES["adapter"]

        with pytest.raises(TypeError, match="ConnectionSettings"):
            TcpConnectivityChecker(
                tcp_config=TcpTestConfig(
                    host=case["host"],
                    port=case["port"],
                ),
                connection_settings=CASES["invalid_dependencies"][
                    "connection_settings"
                ],
            )

    def test_rejects_non_callable_connector(self) -> None:
        """Verify that the injected connector must be callable."""
        case = CASES["adapter"]

        with pytest.raises(TypeError, match="connector must be callable"):
            TcpConnectivityChecker(
                tcp_config=TcpTestConfig(
                    host=case["host"],
                    port=case["port"],
                ),
                connection_settings=ConnectionSettings(
                    timeout_seconds=case["timeout_seconds"]
                ),
                connector=CASES["invalid_dependencies"]["connector"],
            )

    def test_rejects_non_callable_clock(self) -> None:
        """Verify that the injected clock must be callable."""
        case = CASES["adapter"]

        with pytest.raises(TypeError, match="clock must be callable"):
            TcpConnectivityChecker(
                tcp_config=TcpTestConfig(
                    host=case["host"],
                    port=case["port"],
                ),
                connection_settings=ConnectionSettings(
                    timeout_seconds=case["timeout_seconds"]
                ),
                clock=CASES["invalid_dependencies"]["clock"],
            )


@pytest.mark.unit
class TestConnectToTcpTarget:
    """Verify the operating-system TCP connection adapter."""

    def test_opens_and_closes_configured_tcp_connection(self) -> None:
        """Verify that create_connection receives all external settings."""
        case = CASES["adapter"]
        connection = MagicMock()

        with patch(
            "labops_ai.network.tcp_checker.socket.create_connection",
            return_value=connection,
        ) as connector_mock:
            connect_to_tcp_target(
                case["host"],
                case["port"],
                case["timeout_seconds"],
            )

        connector_mock.assert_called_once_with(
            (case["host"], case["port"]),
            timeout=case["timeout_seconds"],
        )

        connection.__enter__.assert_called_once_with()
        connection.__exit__.assert_called_once()