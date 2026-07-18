from __future__ import annotations

import psutil


def collect_system_health() -> dict[str, float]:
    """Collect basic health metrics from the Linux system."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
    }


def main() -> None:
    metrics = collect_system_health()

    print("LabOps AI - System Health")
    print("-------------------------")
    print(f"CPU usage:    {metrics['cpu_percent']:.1f}%")
    print(f"Memory usage: {metrics['memory_percent']:.1f}%")
    print(f"Disk usage:   {metrics['disk_percent']:.1f}%")


if __name__ == "__main__":
    main()
