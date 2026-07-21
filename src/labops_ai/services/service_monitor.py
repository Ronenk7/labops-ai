"""Evaluate Linux service results and overall service health."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from labops_ai.health_status import HealthStatus
from labops_ai.services.service_config import ServiceMonitorConfig
from labops_ai.services.service_result import (
    ServiceCheckResult,
    ServiceCheckStatus,
)


class ServiceChecker(Protocol):
    """Describe the service checker dependency."""

    def check(
        self,
        target: object,
    ) -> ServiceCheckResult:
        """Check one service target."""


@dataclass(frozen=True, slots=True)
class ServiceHealthRecord:
    """Combine one service result with its health severity."""

    result: ServiceCheckResult
    health_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate the health record."""
        if not isinstance(self.result, ServiceCheckResult):
            raise TypeError(
                "result must be a ServiceCheckResult instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError(
                "health_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class ServiceMonitoringSummary:
    """Represent all monitored services and overall health."""

    records: tuple[ServiceHealthRecord, ...]
    overall_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate the monitoring summary."""
        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple.")

        if not self.records:
            raise ValueError(
                "Service monitoring records must not be empty."
            )

        for record in self.records:
            if not isinstance(record, ServiceHealthRecord):
                raise TypeError(
                    "Every record must be a "
                    "ServiceHealthRecord instance."
                )

        if not isinstance(self.overall_status, HealthStatus):
            raise TypeError(
                "overall_status must be a HealthStatus instance."
            )


@dataclass(frozen=True, slots=True)
class ServiceMonitor:
    """Run configured service checks and evaluate their health."""

    config: ServiceMonitorConfig
    checker: ServiceChecker

    def __post_init__(self) -> None:
        """Validate configuration and checker dependency."""
        if not isinstance(self.config, ServiceMonitorConfig):
            raise TypeError(
                "config must be a ServiceMonitorConfig instance."
            )

        if not callable(getattr(self.checker, "check", None)):
            raise TypeError(
                "checker must provide a callable check method."
            )

    def run(self) -> ServiceMonitoringSummary:
        """Check every configured service."""
        records: list[ServiceHealthRecord] = []

        if not self.config.enabled:
            records_tuple = tuple(
                ServiceHealthRecord(
                    result=ServiceCheckResult(
                        service_name=(
                            target.service_name
                        ),
                        label=target.label,
                        status=(
                            ServiceCheckStatus
                            .NOT_APPLICABLE
                        ),
                    ),
                    health_status=(
                        HealthStatus.HEALTHY
                    ),
                )
                for target in self.config.services
            )

            return ServiceMonitoringSummary(
                records=records_tuple,
                overall_status=HealthStatus.HEALTHY,
            )


        for target in self.config.services:
            result = self.checker.check(target)

            if not isinstance(result, ServiceCheckResult):
                raise TypeError(
                    "Service checker must return "
                    "a ServiceCheckResult instance."
                )

            if result.service_name != target.service_name:
                raise ValueError(
                    "Service checker returned a result "
                    "for an unexpected service."
                )

            records.append(
                ServiceHealthRecord(
                    result=result,
                    health_status=self.evaluate_result(result),
                )
            )

        records_tuple = tuple(records)

        return ServiceMonitoringSummary(
            records=records_tuple,
            overall_status=self.get_overall_status(records_tuple),
        )

    @staticmethod
    def evaluate_result(
        result: ServiceCheckResult,
    ) -> HealthStatus:
        """Convert a normalized service state into health severity."""
        if not isinstance(result, ServiceCheckResult):
            raise TypeError(
                "result must be a ServiceCheckResult instance."
            )

        if result.status in {
            ServiceCheckStatus.ACTIVE,
            ServiceCheckStatus.NOT_APPLICABLE,
        }:
            return HealthStatus.HEALTHY

        if result.status is ServiceCheckStatus.TRANSITIONING:
            return HealthStatus.WARNING

        return HealthStatus.CRITICAL

    @staticmethod
    def get_overall_status(
        records: tuple[ServiceHealthRecord, ...],
    ) -> HealthStatus:
        """Return the most severe service health status."""
        if not records:
            raise ValueError(
                "Cannot evaluate an empty service record collection."
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