"""Build human-readable Linux process health reports."""
from __future__ import annotations

from labops_ai.processes.process_config import ProcessReportConfig
from labops_ai.processes.process_monitor import (
    ProcessHealthRecord,
    ProcessMonitoringSummary,
)


def build_process_report(
    summary: ProcessMonitoringSummary,
    report: ProcessReportConfig,
) -> str:
    """Build a process health report."""
    if not isinstance(summary, ProcessMonitoringSummary):
        raise TypeError(
            "summary must be a ProcessMonitoringSummary instance."
        )

    if not isinstance(report, ProcessReportConfig):
        raise TypeError(
            "report must be a ProcessReportConfig instance."
        )

    lines = [
        report.title,
        report.separator,
    ]

    for index, record in enumerate(summary.records):
        if index > 0:
            lines.append("")

        lines.extend(
            _build_record_lines(
                record=record,
                report=report,
            )
        )

    lines.extend(
        [
            report.separator,
            (
                f"{report.overall_label}: "
                f"{summary.overall_status.value}"
            ),
        ]
    )

    return "\n".join(lines)


def print_process_report(
    summary: ProcessMonitoringSummary,
    report: ProcessReportConfig,
) -> None:
    """Print a process health report."""
    print(
        build_process_report(
            summary=summary,
            report=report,
        )
    )


def _build_record_lines(
    record: ProcessHealthRecord,
    report: ProcessReportConfig,
) -> list[str]:
    """Build report lines for one monitored process."""
    result = record.result
    required_value = (
        report.yes_value
        if result.required
        else report.no_value
    )

    lines = [
        f"{report.process_label}: {result.label}",
        f"{report.name_label}: {result.process_name}",
        f"{report.required_label}: {required_value}",
        (
            f"{report.check_status_label}: "
            f"{result.status.value}"
        ),
        (
            f"{report.health_label}: "
            f"{record.health_status.value}"
        ),
    ]

    if result.instances:
        decimal_places = report.decimal_places
        pids = ", ".join(
            str(pid)
            for pid in result.pids
        )

        lines.extend(
            [
                (
                    f"{report.instances_label}: "
                    f"{len(result.instances)}"
                ),
                f"{report.pids_label}: {pids}",
                (
                    f"{report.cpu_label}: "
                    f"{result.total_cpu_percent:.{decimal_places}f}"
                    f"{report.cpu_unit}"
                ),
                (
                    f"{report.memory_label}: "
                    f"{result.total_memory_mb:.{decimal_places}f} "
                    f"{report.memory_unit}"
                ),
                (
                    f"{report.runtime_label}: "
                    f"{result.longest_runtime_seconds:.{decimal_places}f} "
                    f"{report.runtime_unit}"
                ),
            ]
        )

    if result.failure_reason is not None:
        lines.append(
            f"{report.failure_reason_label}: "
            f"{result.failure_reason.value}"
        )

    if result.error_message is not None:
        lines.append(
            f"{report.error_message_label}: "
            f"{result.error_message}"
        )

    return lines