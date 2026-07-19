"""Structured result models for log analysis."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from labops_ai.health_status import HealthStatus


class LogScanStatus(StrEnum):
    """Define normalized log scanning outcomes."""

    ANALYZED = "ANALYZED"
    CHECK_ERROR = "CHECK_ERROR"


class LogFailureReason(StrEnum):
    """Define normalized log scanning failure reasons."""

    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    DECODE_ERROR = "DECODE_ERROR"
    READ_ERROR = "READ_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class LogLine:
    """Represent one line read from a log file."""

    line_number: int
    text: str

    def __post_init__(self) -> None:
        """Validate one log line."""
        if isinstance(self.line_number, bool) or not isinstance(
            self.line_number,
            int,
        ):
            raise TypeError("line_number must be an integer.")

        if self.line_number <= 0:
            raise ValueError(
                "line_number must be greater than zero."
            )

        if not isinstance(self.text, str):
            raise TypeError("Log line text must be a string.")


@dataclass(frozen=True, slots=True)
class LogMatch:
    """Represent one rule match found in a log line."""

    rule_id: str
    rule_label: str
    severity: HealthStatus
    line_number: int
    content: str

    def __post_init__(self) -> None:
        """Validate and normalize one log match."""
        rule_id = self._normalize_required_string(
            "Rule ID",
            self.rule_id,
        )
        rule_label = self._normalize_required_string(
            "Rule label",
            self.rule_label,
        )

        if not isinstance(self.severity, HealthStatus):
            raise TypeError(
                "severity must be a HealthStatus instance."
            )

        if self.severity not in {
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        }:
            raise ValueError(
                "Log match severity must be WARNING or CRITICAL."
            )

        if isinstance(self.line_number, bool) or not isinstance(
            self.line_number,
            int,
        ):
            raise TypeError("line_number must be an integer.")

        if self.line_number <= 0:
            raise ValueError(
                "line_number must be greater than zero."
            )

        if not isinstance(self.content, str):
            raise TypeError("Log match content must be a string.")

        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "rule_label", rule_label)

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


@dataclass(frozen=True, slots=True)
class LogSourceResult:
    """Represent the result of scanning one configured log source."""

    source_id: str
    label: str
    path: str
    required: bool
    status: LogScanStatus
    total_lines_scanned: int
    matches: tuple[LogMatch, ...] = ()
    failure_reason: LogFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the source result."""
        source_id = self._normalize_required_string(
            "Source ID",
            self.source_id,
        )
        label = self._normalize_required_string(
            "Source label",
            self.label,
        )
        path = self._normalize_required_string(
            "Source path",
            self.path,
        )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        if not isinstance(self.status, LogScanStatus):
            raise TypeError(
                "status must be a LogScanStatus instance."
            )

        if isinstance(self.total_lines_scanned, bool) or not isinstance(
            self.total_lines_scanned,
            int,
        ):
            raise TypeError(
                "total_lines_scanned must be an integer."
            )

        if self.total_lines_scanned < 0:
            raise ValueError(
                "total_lines_scanned must not be negative."
            )

        if not isinstance(self.matches, tuple):
            raise TypeError("matches must be a tuple.")

        for match in self.matches:
            if not isinstance(match, LogMatch):
                raise TypeError(
                    "Every match must be a LogMatch instance."
                )

        if self.error_message is not None:
            error_message = self._normalize_required_string(
                "Error message",
                self.error_message,
            )
            object.__setattr__(
                self,
                "error_message",
                error_message,
            )

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "path", path)

        self._validate_consistency()

    def _validate_consistency(self) -> None:
        """Validate status, matches, and failure information."""
        if self.status is LogScanStatus.ANALYZED:
            if self.failure_reason is not None:
                raise ValueError(
                    "An analyzed log cannot contain "
                    "a failure reason."
                )

            if self.error_message is not None:
                raise ValueError(
                    "An analyzed log cannot contain "
                    "an error message."
                )

            return

        if self.total_lines_scanned != 0:
            raise ValueError(
                "A failed log scan must report zero scanned lines."
            )

        if self.matches:
            raise ValueError(
                "A failed log scan cannot contain matches."
            )

        if not isinstance(
            self.failure_reason,
            LogFailureReason,
        ):
            raise ValueError(
                "A failed log scan must contain "
                "a failure reason."
            )

        if self.error_message is None:
            raise ValueError(
                "A failed log scan must contain "
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