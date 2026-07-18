from __future__ import annotations
import psutil


WARNING_THRESHOLD = 70.0
CRITICAL_THRESHOLD = 90.0


def collect_system_health() -> dict[str, float]:
    """Collect basic health metrics from the Linux system."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
    }


def evaluate_metric(value: float) -> str:
    """Return the health status for a metric value."""
    if value >= CRITICAL_THRESHOLD:
        return "CRITICAL"

    if value >= WARNING_THRESHOLD:
        return "WARNING"

    return "HEALTHY"


def evaluate_system_health(metrics: dict[str, float]) -> dict[str, str]:
    """Evaluate all collected system metrics."""
    return {
        metric_name: evaluate_metric(value)
        for metric_name, value in metrics.items()
    }


def get_overall_status(statuses: dict[str, str]) -> str:
    """Return the most severe status found in the system."""
    if "CRITICAL" in statuses.values():
        return "CRITICAL"

    if "WARNING" in statuses.values():
        return "WARNING"

    return "HEALTHY"


def main() -> None:
    metrics = collect_system_health()
    statuses = evaluate_system_health(metrics)
    overall_status = get_overall_status(statuses)

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


if __name__ == "__main__":
    main()
