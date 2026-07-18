"""Collect and evaluate Linux system health metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import psutil

from labops_ai.config import (
    HealthThresholdLoader,
    HealthThresholds,
)


class HealthStatus(StrEnum):
    """Define the supported system health severity levels."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


MetricValues = dict[str, float]
MetricStatuses = dict[str, HealthStatus]


@dataclass(frozen=True, slots=True)
class SystemHealthMonitor:
    """
    Collect and evaluate system utilization metrics.

    The monitor receives validated thresholds through dependency
    injection rather than containing hard-coded values.

    Attributes:
        thresholds:
            Warning and critical thresholds used to classify metrics.
    """

    thresholds: HealthThresholds

    def collect_system_health(self) -> MetricValues:
        """
        Collect basic utilization metrics from the Linux system.

        Returns:
            A dictionary containing CPU, memory, and disk usage
            percentages.
        """
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
        }

    def evaluate_metric(
        self,
        value: float,
    ) -> HealthStatus:
        """
        Classify one utilization metric by severity.

        Args:
            value:
                Metric utilization percentage.

        Returns:
            CRITICAL when the value reaches the critical threshold,
            WARNING when it reaches the warning threshold,
            otherwise HEALTHY.
        """
        if value >= self.thresholds.critical:
            return HealthStatus.CRITICAL

        if value >= self.thresholds.warning:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    def evaluate_system_health(
        self,
        metrics: MetricValues,
    ) -> MetricStatuses:
        """
        Classify every supplied system metric.

        Args:
            metrics:
                Mapping between metric names and percentage values.

        Returns:
            A dictionary containing one HealthStatus for every metric.
        """
        return {
            metric_name: self.evaluate_metric(metric_value)
            for metric_name, metric_value in metrics.items()
        }

    @staticmethod
    def get_overall_status(
        statuses: MetricStatuses,
    ) -> HealthStatus:
        """
        Return the most severe status found in the system.

        Args:
            statuses:
                Mapping between metric names and evaluated statuses.

        Returns:
            CRITICAL when at least one metric is critical,
            WARNING when at least one metric is warning,
            otherwise HEALTHY.
        """
        if HealthStatus.CRITICAL in statuses.values():
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses.values():
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY


def print_health_report(
    metrics: MetricValues,
    statuses: MetricStatuses,
    overall_status: HealthStatus,
) -> None:
    """
    Print the collected metrics and their evaluated statuses.

    Args:
        metrics:
            Raw CPU, memory, and disk utilization percentages.

        statuses:
            Evaluated status for every metric.

        overall_status:
            Most severe status found in the system.
    """
    print("LabOps AI - System Health")
    print("-------------------------")

    print(
        f"CPU usage:    {metrics['cpu_percent']:.1f}% "
        f"[{statuses['cpu_percent']}]"
    )

    print(
        f"Memory usage: {metrics['memory_percent']:.1f}% "
        f"[{statuses['memory_percent']}]"
    )

    print(
        f"Disk usage:   {metrics['disk_percent']:.1f}% "
        f"[{statuses['disk_percent']}]"
    )

    print("-------------------------")
    print(f"Overall status: {overall_status}")


def main() -> None:
    """
    Load configuration, evaluate system health, and print the report.

    The function connects the configuration loader, system monitor,
    metric evaluation, and report output.
    """
    thresholds = HealthThresholdLoader().load()

    monitor = SystemHealthMonitor(
        thresholds=thresholds,
    )

    metrics = monitor.collect_system_health()

    statuses = monitor.evaluate_system_health(
        metrics
    )

    overall_status = monitor.get_overall_status(
        statuses
    )

    print_health_report(
        metrics=metrics,
        statuses=statuses,
        overall_status=overall_status,
    )


if __name__ == "__main__":
    main()