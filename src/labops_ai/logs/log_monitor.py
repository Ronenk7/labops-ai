"""Evaluate log scan results and overall log health."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from labops_ai.health_status import HealthStatus
from labops_ai.logs.log_config import (
    LogAnalyzerConfig,
    LogSourceConfig,
)
from labops_ai.logs.log_result import (
    LogScanStatus,
    LogSourceResult,
)


class LogScanner(Protocol):
    """Describe the log scanner dependency."""

    def scan(
        self,
        source: LogSourceConfig,
    ) -> LogSourceResult:
        """Scan one configured log source."""


@dataclass(frozen=True, slots=True)
class LogHealthRecord:
    """Combine a source, scan result, and health severity."""

    source: LogSourceConfig
    result: LogSourceResult
    health_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate one log health record."""
        if not isinstance(self.source, LogSourceConfig):
            raise TypeError(
                "source must be a LogSourceConfig instance."
            )

        if not isinstance(self.result, LogSourceResult):
            raise TypeError(
                "result must be a LogSourceResult instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError(
                "health_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class LogAnalysisSummary:
    """Represent all log records and overall health."""

    records: tuple[LogHealthRecord, ...]
    overall_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate the complete log analysis summary."""
        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple.")

        if not self.records:
            raise ValueError(
                "Log analysis records must not be empty."
            )

        for record in self.records:
            if not isinstance(record, LogHealthRecord):
                raise TypeError(
                    "Every record must be a "
                    "LogHealthRecord instance."
                )

        if not isinstance(self.overall_status, HealthStatus):
            raise TypeError(
                "overall_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class LogAnalyzer:
    """Run configured log scans and evaluate health."""

    config: LogAnalyzerConfig
    scanner: LogScanner

    def __post_init__(self) -> None:
        """Validate configuration and scanner dependency."""
        if not isinstance(self.config, LogAnalyzerConfig):
            raise TypeError(
                "config must be a LogAnalyzerConfig instance."
            )

        if not callable(getattr(self.scanner, "scan", None)):
            raise TypeError(
                "scanner must provide a callable scan method."
            )

    def run(self) -> LogAnalysisSummary:
        """Scan every configured log source."""
        records: list[LogHealthRecord] = []

        for source in self.config.sources:
            result = self.scanner.scan(source)

            if not isinstance(result, LogSourceResult):
                raise TypeError(
                    "Log scanner must return "
                    "a LogSourceResult instance."
                )

            if (
                result.source_id.casefold()
                != source.source_id.casefold()
            ):
                raise ValueError(
                    "Log scanner returned a result "
                    "for an unexpected source."
                )

            if result.path != source.path:
                raise ValueError(
                    "Log scanner returned an unexpected source path."
                )

            if result.required is not source.required:
                raise ValueError(
                    "Log scanner returned an unexpected "
                    "required setting."
                )

            records.append(
                LogHealthRecord(
                    source=source,
                    result=result,
                    health_status=self.evaluate_result(result),
                )
            )

        records_tuple = tuple(records)

        return LogAnalysisSummary(
            records=records_tuple,
            overall_status=self.get_overall_status(
                records_tuple
            ),
        )

    @staticmethod
    def evaluate_result(
        result: LogSourceResult,
    ) -> HealthStatus:
        """Convert one log source result into health severity."""
        if not isinstance(result, LogSourceResult):
            raise TypeError(
                "result must be a LogSourceResult instance."
            )

        if result.status is LogScanStatus.CHECK_ERROR:
            if result.required:
                return HealthStatus.CRITICAL

            return HealthStatus.WARNING

        severities = {
            match.severity
            for match in result.matches
        }

        if HealthStatus.CRITICAL in severities:
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in severities:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def get_overall_status(
        records: tuple[LogHealthRecord, ...],
    ) -> HealthStatus:
        """Return the highest log health severity."""
        if not records:
            raise ValueError(
                "Cannot evaluate an empty log record collection."
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