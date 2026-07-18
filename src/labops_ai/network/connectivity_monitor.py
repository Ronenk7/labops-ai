"""Run and evaluate DNS and TCP connectivity checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from labops_ai.health_status import HealthStatus
from labops_ai.network.connectivity_config import ConnectivityConfig
from labops_ai.network.connectivity_result import (ConnectivityCheckResult, ConnectivityCheckStatus, ConnectivityCheckType)


class ConnectivityChecker(Protocol):
    """Define the interface required from a connectivity checker."""

    def check(self) -> ConnectivityCheckResult:
        """Run one connectivity check and return its structured result."""


@dataclass(frozen=True, slots=True)
class NetworkConnectivitySummary:
    """Represent the evaluated result of all network connectivity checks."""

    dns_result: ConnectivityCheckResult
    dns_status: HealthStatus
    tcp_result: ConnectivityCheckResult
    tcp_status: HealthStatus
    overall_status: HealthStatus


@dataclass(frozen=True, slots=True)
class NetworkConnectivityMonitor:
    """Run and evaluate the configured DNS and TCP connectivity checks."""

    config: ConnectivityConfig
    dns_checker: ConnectivityChecker
    tcp_checker: ConnectivityChecker

    def __post_init__(self) -> None:
        """Validate configuration and injected connectivity checkers."""
        if not isinstance(self.config, ConnectivityConfig):
            raise TypeError("config must be a ConnectivityConfig instance.")

        self._validate_checker("dns_checker", self.dns_checker)
        self._validate_checker("tcp_checker", self.tcp_checker)

    def run(self) -> NetworkConnectivitySummary:
        """Run DNS and TCP checks and return their evaluated summary."""
        dns_result = self._run_expected_check(checker=self.dns_checker, expected_type=ConnectivityCheckType.DNS)
        tcp_result = self._run_expected_check(checker=self.tcp_checker, expected_type=ConnectivityCheckType.TCP)
        dns_status = self.evaluate_result(dns_result)
        tcp_status = self.evaluate_result(tcp_result)
        overall_status = self.get_overall_status(dns_status, tcp_status)

        return NetworkConnectivitySummary(dns_result=dns_result, dns_status=dns_status, tcp_result=tcp_result, tcp_status=tcp_status, overall_status=overall_status)

    def evaluate_result(self, result: ConnectivityCheckResult) -> HealthStatus:
        """Classify one connectivity result using configured latency thresholds."""
        if not isinstance(result, ConnectivityCheckResult):
            raise TypeError("result must be a ConnectivityCheckResult instance.")

        if result.status is ConnectivityCheckStatus.FAILED:
            return HealthStatus.CRITICAL

        if result.latency_ms is None:
            raise ValueError("A passed connectivity result must contain latency.")

        thresholds = self.config.latency_thresholds_ms

        if result.latency_ms >= thresholds.critical:
            return HealthStatus.CRITICAL

        if result.latency_ms >= thresholds.warning:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def get_overall_status(*statuses: HealthStatus) -> HealthStatus:
        """Return the most severe supplied network health status."""
        if not statuses:
            raise ValueError("At least one health status is required.")

        if any(not isinstance(status, HealthStatus) for status in statuses):
            raise TypeError("Every status must be a HealthStatus instance.")

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def _validate_checker(field_name: str, checker: object) -> None:
        """Verify that an injected checker provides a callable check method."""
        if not callable(getattr(checker, "check", None)):
            raise TypeError(f"{field_name} must provide a callable check method.")

    @staticmethod
    def _run_expected_check(checker: ConnectivityChecker, expected_type: ConnectivityCheckType) -> ConnectivityCheckResult:
        """Run one checker and validate the returned check type."""
        result = checker.check()

        if not isinstance(result, ConnectivityCheckResult):
            raise TypeError("Connectivity checker must return ConnectivityCheckResult.")

        if result.check_type is not expected_type:
            raise ValueError(f"Expected {expected_type} result, received {result.check_type}.")

        return result