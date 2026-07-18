"""Structured result models for network connectivity checks."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ConnectivityCheckType(StrEnum):
    """Define the supported network connectivity checks."""

    DNS = "DNS"
    TCP = "TCP"


class ConnectivityCheckStatus(StrEnum):
    """Define the possible connectivity check outcomes."""

    PASSED = "PASSED"
    FAILED = "FAILED"


class ConnectivityFailureReason(StrEnum):
    """Define normalized reasons for connectivity check failures."""

    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    TCP_CONNECTION_FAILED = "TCP_CONNECTION_FAILED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class ConnectivityCheckResult:
    """Represent the structured result of one connectivity check."""

    check_type: ConnectivityCheckType
    status: ConnectivityCheckStatus
    target: str
    latency_ms: float | None = None
    resolved_address: str | None = None
    failure_reason: ConnectivityFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the connectivity result."""
        if not isinstance(self.check_type, ConnectivityCheckType):
            raise TypeError("check_type must be a ConnectivityCheckType instance.")

        if not isinstance(self.status, ConnectivityCheckStatus):
            raise TypeError("status must be a ConnectivityCheckStatus instance.")

        if not isinstance(self.target, str):
            raise TypeError("Connectivity target must be a string.")

        normalized_target = self.target.strip()

        if not normalized_target:
            raise ValueError("Connectivity target must not be empty.")

        object.__setattr__(self, "target", normalized_target)

        if self.latency_ms is not None:
            normalized_latency = self._normalize_latency(self.latency_ms)
            object.__setattr__(self, "latency_ms", normalized_latency)

        if self.resolved_address is not None:
            normalized_address = self._normalize_optional_string(
                "Resolved address",
                self.resolved_address,
            )
            object.__setattr__(self, "resolved_address", normalized_address)

        if self.error_message is not None:
            normalized_message = self._normalize_optional_string(
                "Error message",
                self.error_message,
            )
            object.__setattr__(self, "error_message", normalized_message)

        self._validate_result_consistency()

    @staticmethod
    def _normalize_latency(value: object) -> float:
        """Validate and normalize a connectivity latency value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Connectivity latency must be a numeric value.")

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError("Connectivity latency must be a finite value.")

        if normalized_value < 0.0:
            raise ValueError("Connectivity latency must not be negative.")

        return normalized_value

    @staticmethod
    def _normalize_optional_string(field_name: str, value: object) -> str:
        """Validate and normalize a populated optional string."""
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty.")

        return normalized_value

    def _validate_result_consistency(self) -> None:
        """Verify consistency between status and failure information."""
        if self.status is ConnectivityCheckStatus.PASSED:
            if self.failure_reason is not None or self.error_message is not None:
                raise ValueError("A passed connectivity check cannot contain failure details.")

        if self.status is ConnectivityCheckStatus.FAILED:
            if not isinstance(self.failure_reason, ConnectivityFailureReason):
                raise ValueError("A failed connectivity check must contain a failure reason.")