"""Collect, evaluate, and report Linux system health metrics."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import psutil
from labops_ai.config import (SystemHealthConfig, SystemHealthConfigLoader, SystemHealthReportConfig)


class HealthStatus(StrEnum):
    """Define the supported system health severity levels."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


MetricValues = dict[str, float]
MetricStatuses = dict[str, HealthStatus]


@dataclass(frozen=True, slots=True)
class SystemHealthMonitor:
    """Collect and evaluate system utilization metrics."""

    config: SystemHealthConfig

    def collect_system_health(self) -> MetricValues:
        """Collect CPU, memory, and disk utilization metrics."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(self.config.collection.disk_mount_point)

        return {
            "cpu_percent": psutil.cpu_percent(interval=self.config.collection.cpu_sample_interval_seconds),
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
        }

    def evaluate_metric(self, metric_name: str, value: float) -> HealthStatus:
        """Classify one metric using its externally configured thresholds."""
        thresholds = self.config.metric_thresholds[metric_name]

        if value >= thresholds.critical:
            return HealthStatus.CRITICAL

        if value >= thresholds.warning:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    def evaluate_system_health(self, metrics: MetricValues) -> MetricStatuses:
        """Classify every supplied system metric."""
        return {metric_name: self.evaluate_metric(metric_name, metric_value) for metric_name, metric_value in metrics.items()}

    @staticmethod
    def get_overall_status(statuses: MetricStatuses) -> HealthStatus:
        """Return the most severe status found in the system."""
        if HealthStatus.CRITICAL in statuses.values():
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses.values():
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY


def print_health_report(metrics: MetricValues, statuses: MetricStatuses, overall_status: HealthStatus, report: SystemHealthReportConfig) -> None:
    """Print a system health report using external report configuration."""
    print(report.title)
    print(report.separator)

    for metric_name, metric_label in report.metric_labels.items():
        print(f"{metric_label}: {metrics[metric_name]:.1f}% [{statuses[metric_name]}]")

    print(report.separator)
    print(f"{report.overall_label}: {overall_status}")


def main() -> None:
    """Load configuration, evaluate system health, and print the report."""
    config = SystemHealthConfigLoader().load()
    monitor = SystemHealthMonitor(config=config)
    metrics = monitor.collect_system_health()
    statuses = monitor.evaluate_system_health(metrics)
    overall_status = monitor.get_overall_status(statuses)

    print_health_report(metrics=metrics, statuses=statuses, overall_status=overall_status, report=config.report)


if __name__ == "__main__":
    main()