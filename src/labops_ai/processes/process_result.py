"""Structured result models for Linux process checks."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ProcessCheckStatus(StrEnum):
    """Define normalized process check outcomes."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"
    CHECK_ERROR = "CHECK_ERROR"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProcessFailureReason(StrEnum):
    """Define normalized process check failure reasons."""

    ACCESS_DENIED = "ACCESS_DENIED"
    PROCESS_SCAN_FAILED = "PROCESS_SCAN_FAILED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class ProcessInstanceSnapshot:
    """Represent metrics for one running process instance."""

    pid: int
    cpu_percent: float
    memory_mb: float
    runtime_seconds: float

    def __post_init__(self) -> None:
        """Validate one process instance snapshot."""
        if isinstance(self.pid, bool) or not isinstance(self.pid, int):
            raise TypeError("pid must be an integer.")

        if self.pid <= 0:
            raise ValueError("pid must be greater than zero.")

        for field_name in (
            "cpu_percent",
            "memory_mb",
            "runtime_seconds",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(
                    f"{field_name} must be numeric."
                )

            normalized_value = float(value)

            if not isfinite(normalized_value):
                raise ValueError(
                    f"{field_name} must be finite."
                )

            if normalized_value < 0.0:
                raise ValueError(
                    f"{field_name} must not be negative."
                )

            object.__setattr__(
                self,
                field_name,
                normalized_value,
            )


@dataclass(frozen=True, slots=True)
class ProcessCheckResult:
    """Represent the complete result of one process check."""

    process_name: str
    label: str
    required: bool
    status: ProcessCheckStatus
    instances: tuple[ProcessInstanceSnapshot, ...] = ()
    failure_reason: ProcessFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the process result."""
        process_name = self._normalize_required_string(
            "Process name",
            self.process_name,
        )
        label = self._normalize_required_string(
            "Process label",
            self.label,
        )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        if not isinstance(self.status, ProcessCheckStatus):
            raise TypeError(
                "status must be a ProcessCheckStatus instance."
            )

        if not isinstance(self.instances, tuple):
            raise TypeError("instances must be a tuple.")

        for instance in self.instances:
            if not isinstance(instance, ProcessInstanceSnapshot):
                raise TypeError(
                    "Every instance must be a "
                    "ProcessInstanceSnapshot."
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

        object.__setattr__(
            self,
            "process_name",
            process_name,
        )
        object.__setattr__(self, "label", label)

        self._validate_consistency()

    @property
    def total_cpu_percent(self) -> float:
        """Return total CPU usage across all matching instances."""
        return sum(
            instance.cpu_percent
            for instance in self.instances
        )

    @property
    def total_memory_mb(self) -> float:
        """Return total memory across all matching instances."""
        return sum(
            instance.memory_mb
            for instance in self.instances
        )

    @property
    def longest_runtime_seconds(self) -> float:
        """Return the longest runtime among matching instances."""
        return max(
            (
                instance.runtime_seconds
                for instance in self.instances
            ),
            default=0.0,
        )

    @property
    def pids(self) -> tuple[int, ...]:
        """Return matching process IDs."""
        return tuple(
            instance.pid
            for instance in self.instances
        )

    def _validate_consistency(self) -> None:
        """Validate status, instances, and error consistency."""
        if (
            self.status
            is ProcessCheckStatus.NOT_APPLICABLE
        ):
            if self.instances:
                raise ValueError(
                    "A not-applicable process cannot "
                    "contain instances."
                )

            if (
                self.failure_reason is not None
                or self.error_message is not None
            ):
                raise ValueError(
                    "A not-applicable process cannot "
                    "contain failure details."
                )

            return

        if self.status is ProcessCheckStatus.RUNNING:
            if not self.instances:
                raise ValueError(
                    "A running process result must contain instances."
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "A running result cannot contain "
                    "a failure reason."
                )

            if self.error_message is not None:
                raise ValueError(
                    "A running result cannot contain "
                    "an error message."
                )

            return

        if self.instances:
            raise ValueError(
                "A non-running result cannot contain instances."
            )

        if self.status is ProcessCheckStatus.NOT_RUNNING:
            if self.failure_reason is not None:
                raise ValueError(
                    "A not-running result cannot contain "
                    "a failure reason."
                )

            if self.error_message is not None:
                raise ValueError(
                    "A not-running result cannot contain "
                    "an error message."
                )

            return

        if not isinstance(
            self.failure_reason,
            ProcessFailureReason,
        ):
            raise ValueError(
                "A process check error must contain "
                "a failure reason."
            )

        if self.error_message is None:
            raise ValueError(
                "A process check error must contain "
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