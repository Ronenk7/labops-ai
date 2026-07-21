"""Structured result models for Linux service checks."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ServiceCheckStatus(StrEnum):
    """Define normalized Linux service states."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"
    TRANSITIONING = "TRANSITIONING"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"
    CHECK_ERROR = "CHECK_ERROR"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ServiceFailureReason(StrEnum):
    """Define normalized service check failure reasons."""

    UNIT_NOT_FOUND = "UNIT_NOT_FOUND"
    SYSTEMCTL_NOT_FOUND = "SYSTEMCTL_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    COMMAND_FAILED = "COMMAND_FAILED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class ServiceCheckResult:
    """Represent the result of one Linux service check."""

    service_name: str
    label: str
    status: ServiceCheckStatus
    load_state: str | None = None
    active_state: str | None = None
    sub_state: str | None = None
    failure_reason: ServiceFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the service check result."""
        normalized_name = self._normalize_required_string(
            "Service name",
            self.service_name,
        )
        normalized_label = self._normalize_required_string(
            "Service label",
            self.label,
        )

        if not isinstance(self.status, ServiceCheckStatus):
            raise TypeError(
                "status must be a ServiceCheckStatus instance."
            )

        object.__setattr__(self, "service_name", normalized_name)
        object.__setattr__(self, "label", normalized_label)

        for field_name in (
            "load_state",
            "active_state",
            "sub_state",
            "error_message",
        ):
            value = getattr(self, field_name)

            if value is not None:
                normalized_value = self._normalize_required_string(
                    field_name.replace("_", " ").title(),
                    value,
                )
                object.__setattr__(
                    self,
                    field_name,
                    normalized_value,
                )

        self._validate_consistency()

    def _validate_consistency(self) -> None:
        """Validate state and failure information consistency."""
        raw_states = (
            self.load_state,
            self.active_state,
            self.sub_state,
        )

        if (
            self.status
            is ServiceCheckStatus.NOT_APPLICABLE
        ):
            if any(
                state is not None
                for state in raw_states
            ):
                raise ValueError(
                    "A not-applicable service cannot "
                    "contain raw states."
                )

            if (
                self.failure_reason is not None
                or self.error_message is not None
            ):
                raise ValueError(
                    "A not-applicable service cannot "
                    "contain failure details."
                )

            return

        if self.status is ServiceCheckStatus.CHECK_ERROR:
            if any(state is not None for state in raw_states):
                raise ValueError(
                    "A service check error cannot contain raw states."
                )

            if not isinstance(
                self.failure_reason,
                ServiceFailureReason,
            ):
                raise ValueError(
                    "A service check error must contain a failure reason."
                )

            if self.error_message is None:
                raise ValueError(
                    "A service check error must contain an error message."
                )

            return

        if any(state is None for state in raw_states):
            raise ValueError(
                "A completed service check must contain all raw states."
            )

        if self.status is ServiceCheckStatus.NOT_FOUND:
            if (
                self.failure_reason
                is not ServiceFailureReason.UNIT_NOT_FOUND
            ):
                raise ValueError(
                    "A missing service must use UNIT_NOT_FOUND."
                )

            return

        if self.failure_reason is not None:
            raise ValueError(
                "A completed service check cannot contain "
                "a failure reason."
            )

        if self.error_message is not None:
            raise ValueError(
                "A completed service check cannot contain "
                "an error message."
            )

    @staticmethod
    def _normalize_required_string(
        field_name: str,
        value: object,
    ) -> str:
        """Validate and normalize a populated string."""
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty.")

        return normalized_value