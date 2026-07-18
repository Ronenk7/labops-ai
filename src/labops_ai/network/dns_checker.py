"""Perform DNS connectivity checks and return structured results."""
from __future__ import annotations
import socket
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from labops_ai.network.connectivity_config import DnsTestConfig
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)


DnsResolver = Callable[[str], str]
Clock = Callable[[], float]


def resolve_hostname(hostname: str) -> str:
    """
    Resolve a hostname and return its first available IP address.

    Args:
        hostname:
            Hostname to resolve.

    Returns:
        The first IPv4 or IPv6 address returned by the operating system.

    Raises:
        socket.gaierror:
            If DNS resolution fails or returns no addresses.
    """
    address_info = socket.getaddrinfo(
        hostname,
        None,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
    )

    if not address_info:
        raise socket.gaierror(f"No IP address was returned for {hostname}.")

    return address_info[0][4][0]


@dataclass(frozen=True, slots=True)
class DnsConnectivityChecker:
    """Perform a DNS resolution check using external configuration."""

    config: DnsTestConfig
    resolver: DnsResolver = resolve_hostname
    clock: Clock = perf_counter

    def __post_init__(self) -> None:
        """Validate injected configuration and dependencies."""
        if not isinstance(self.config, DnsTestConfig):
            raise TypeError("config must be a DnsTestConfig instance.")

        if not callable(self.resolver):
            raise TypeError("resolver must be callable.")

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def check(self) -> ConnectivityCheckResult:
        """
        Resolve the configured hostname and return a structured result.

        Returns:
            A passed result containing the resolved address and latency,
            or a failed result containing a normalized failure reason.
        """
        start_time = self.clock()

        try:
            resolved_address = self.resolver(self.config.hostname)
            latency_ms = (self.clock() - start_time) * 1000.0

            return ConnectivityCheckResult(
                check_type=ConnectivityCheckType.DNS,
                status=ConnectivityCheckStatus.PASSED,
                target=self.config.hostname,
                latency_ms=latency_ms,
                resolved_address=resolved_address,
            )
        except socket.gaierror as error:
            return self._build_failed_result(
                reason=ConnectivityFailureReason.DNS_RESOLUTION_FAILED,
                error=error,
                fallback_message="DNS resolution failed.",
            )
        except TimeoutError as error:
            return self._build_failed_result(
                reason=ConnectivityFailureReason.TIMEOUT,
                error=error,
                fallback_message="DNS resolution timed out.",
            )
        except OSError as error:
            return self._build_failed_result(
                reason=ConnectivityFailureReason.UNKNOWN_ERROR,
                error=error,
                fallback_message="An operating system error interrupted DNS resolution.",
            )

    def _build_failed_result(
        self,
        reason: ConnectivityFailureReason,
        error: OSError,
        fallback_message: str,
    ) -> ConnectivityCheckResult:
        """Build a normalized failed DNS result."""
        error_message = str(error).strip() or fallback_message

        return ConnectivityCheckResult(
            check_type=ConnectivityCheckType.DNS,
            status=ConnectivityCheckStatus.FAILED,
            target=self.config.hostname,
            failure_reason=reason,
            error_message=error_message,
        )