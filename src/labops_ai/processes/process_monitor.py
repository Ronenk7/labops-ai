"""Evaluate process metrics and overall process health."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from labops_ai.health_status import HealthStatus
from labops_ai.processes.process_config import (
    ProcessMonitorConfig,
    ProcessTargetConfig,
)
from labops_ai.processes.process_result import (
    ProcessCheckResult,
    ProcessCheckStatus,
)


class ProcessChecker(Protocol):
    """Describe the process checker dependency."""

    def check(
        self,
        target: ProcessTargetConfig,
    ) -> ProcessCheckResult:
        """Check one configured process."""


@dataclass(frozen=True, slots=True)
class ProcessHealthRecord:
    """Combine a target, result, and calculated health status."""

    target: ProcessTargetConfig
    result: ProcessCheckResult
    health_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate one process health record."""
        if not isinstance(self.target, ProcessTargetConfig):
            raise TypeError(
                "target must be a ProcessTargetConfig instance."
            )

        if not isinstance(self.result, ProcessCheckResult):
            raise TypeError(
                "result must be a ProcessCheckResult instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError(
                "health_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class ProcessMonitoringSummary:
    """Represent all process records and overall health."""

    records: tuple[ProcessHealthRecord, ...]
    overall_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate the complete process summary."""
        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple.")

        if not self.records:
            raise ValueError(
                "Process monitoring records must not be empty."
            )

        for record in self.records:
            if not isinstance(record, ProcessHealthRecord):
                raise TypeError(
                    "Every record must be a "
                    "ProcessHealthRecord instance."
                )

        if not isinstance(self.overall_status, HealthStatus):
            raise TypeError(
                "overall_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class ProcessMonitor:
    """Run configured process checks and evaluate health."""

    config: ProcessMonitorConfig
    checker: ProcessChecker

    def __post_init__(self) -> None:
        """Validate the monitor configuration and checker."""
        if not isinstance(self.config, ProcessMonitorConfig):
            raise TypeError(
                "config must be a ProcessMonitorConfig instance."
            )

        if not callable(getattr(self.checker, "check", None)):
            raise TypeError(
                "checker must provide a callable check method."
            )

    def run(self) -> ProcessMonitoringSummary:
        """Check all configured process targets."""
        records: list[ProcessHealthRecord] = []

        for target in self.config.processes:
            if target.enabled:
                result = self.checker.check(target)
            else:
                result = ProcessCheckResult(
                    process_name=target.process_name,
                    label=target.label,
                    required=target.required,
                    status=(
                        ProcessCheckStatus
                        .NOT_APPLICABLE
                    ),
                )

            if not isinstance(result, ProcessCheckResult):
                raise TypeError(
                    "Process checker must return "
                    "a ProcessCheckResult instance."
                )

            if (
                result.process_name.casefold()
                != target.process_name.casefold()
            ):
                raise ValueError(
                    "Process checker returned a result "
                    "for an unexpected process."
                )

            if result.required is not target.required:
                raise ValueError(
                    "Process checker returned an unexpected "
                    "required setting."
                )

            records.append(
                ProcessHealthRecord(
                    target=target,
                    result=result,
                    health_status=self.evaluate_result(
                        target=target,
                        result=result,
                    ),
                )
            )

        records_tuple = tuple(records)

        return ProcessMonitoringSummary(
            records=records_tuple,
            overall_status=self.get_overall_status(
                records_tuple
            ),
        )

    @staticmethod
    def evaluate_result(
        target: ProcessTargetConfig,
        result: ProcessCheckResult,
    ) -> HealthStatus:
        """Convert one process result into health severity."""
        if not isinstance(target, ProcessTargetConfig):
            raise TypeError(
                "target must be a ProcessTargetConfig instance."
            )

        if not isinstance(result, ProcessCheckResult):
            raise TypeError(
                "result must be a ProcessCheckResult instance."
            )

        if (
            result.status
            is ProcessCheckStatus.NOT_APPLICABLE
        ):
            return HealthStatus.HEALTHY

        if result.status is ProcessCheckStatus.CHECK_ERROR:
            return HealthStatus.CRITICAL

        if result.status is ProcessCheckStatus.NOT_RUNNING:
            if target.required:
                return HealthStatus.CRITICAL

            return HealthStatus.WARNING

        cpu_thresholds = target.cpu_thresholds_percent
        memory_thresholds = target.memory_thresholds_mb

        if (
            result.total_cpu_percent >= cpu_thresholds.critical
            or result.total_memory_mb >= memory_thresholds.critical
        ):
            return HealthStatus.CRITICAL

        if (
            result.total_cpu_percent >= cpu_thresholds.warning
            or result.total_memory_mb >= memory_thresholds.warning
        ):
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def get_overall_status(
        records: tuple[ProcessHealthRecord, ...],
    ) -> HealthStatus:
        """Return the highest process health severity."""
        if not records:
            raise ValueError(
                "Cannot evaluate an empty process record collection."
            )

        statuses = {
            record.health_status
            for record in records
        }

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY