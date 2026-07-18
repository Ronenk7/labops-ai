"""Perform TCP connectivity checks and return structured results."""
from __future__ import annotations
import socket
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from labops_ai.network.connectivity_config import ConnectionSettings, TcpTestConfig
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)


TcpConnector = Callable[[str, int, float], None]
Clock = Callable[[], float]


def connect_to_tcp_target(host: str, port: int, timeout_seconds: float) -> None:
    """
    Open and close a TCP connection to the supplied target.

    Args:
        host:
            IPv4 or IPv6 address of the remote target.

        port:
            TCP port used for the connection.

        timeout_seconds:
            Maximum time allowed for establishing the connection.

    Raises:
        TimeoutError:
            If the connection attempt exceeds the configured timeout.

        OSError:
            If the operating system cannot establish the connection.
    """
    with socket.create_connection((host, port), timeout=timeout_seconds):
        return


@dataclass(frozen=True, slots=True)
class TcpConnectivityChecker:
    """Perform a TCP connection check using external configuration."""

    tcp_config: TcpTestConfig
    connection_settings: ConnectionSettings
    connector: TcpConnector = connect_to_tcp_target
    clock: Clock = perf_counter

    def __post_init__(self) -> None:
        """Validate injected configuration and dependencies."""
        if not isinstance(self.tcp_config, TcpTestConfig):
            raise TypeError("tcp_config must be a TcpTestConfig instance.")

        if not isinstance(self.connection_settings, ConnectionSettings):
            raise TypeError(
                "connection_settings must be a ConnectionSettings instance."
            )

        if not callable(self.connector):
            raise TypeError("connector must be callable.")

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def check(self) -> ConnectivityCheckResult:
        """
        Connect to the configured TCP target and return a structured result.

        Returns:
            A passed result containing connection latency, or a failed
            result containing a normalized failure reason.
        """
        target = self._format_target()

        try:
            start_time = self.clock()

            self.connector(
                self.tcp_config.host,
                self.tcp_config.port,
                self.connection_settings.timeout_seconds,
            )

            latency_ms = (self.clock() - start_time) * 1000.0

            return ConnectivityCheckResult(
                check_type=ConnectivityCheckType.TCP,
                status=ConnectivityCheckStatus.PASSED,
                target=target,
                latency_ms=latency_ms,
            )
        except TimeoutError as error:
            return self._build_failed_result(
                target=target,
                reason=ConnectivityFailureReason.TIMEOUT,
                error=error,
                fallback_message="TCP connection timed out.",
            )
        except OSError as error:
            return self._build_failed_result(
                target=target,
                reason=ConnectivityFailureReason.TCP_CONNECTION_FAILED,
                error=error,
                fallback_message="TCP connection failed.",
            )
        except Exception as error:
            return self._build_failed_result(
                target=target,
                reason=ConnectivityFailureReason.UNKNOWN_ERROR,
                error=error,
                fallback_message="An unexpected TCP connectivity error occurred.",
            )

    def _format_target(self) -> str:
        """Return an unambiguous host and port representation."""
        host = self.tcp_config.host
        port = self.tcp_config.port

        if ":" in host:
            return f"[{host}]:{port}"

        return f"{host}:{port}"

    @staticmethod
    def _build_failed_result(
        target: str,
        reason: ConnectivityFailureReason,
        error: Exception,
        fallback_message: str,
    ) -> ConnectivityCheckResult:
        """Build a normalized failed TCP result."""
        error_message = str(error).strip() or fallback_message

        return ConnectivityCheckResult(
            check_type=ConnectivityCheckType.TCP,
            status=ConnectivityCheckStatus.FAILED,
            target=target,
            failure_reason=reason,
            error_message=error_message,
        )