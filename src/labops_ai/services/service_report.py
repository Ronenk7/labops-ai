"""Build human-readable Linux service health reports."""
from __future__ import annotations

from labops_ai.services.service_config import ServiceReportConfig
from labops_ai.services.service_monitor import (
    ServiceHealthRecord,
    ServiceMonitoringSummary,
)


def build_service_report(
    summary: ServiceMonitoringSummary,
    report: ServiceReportConfig,
) -> str:
    """Build a service health report."""
    if not isinstance(summary, ServiceMonitoringSummary):
        raise TypeError(
            "summary must be a ServiceMonitoringSummary instance."
        )

    if not isinstance(report, ServiceReportConfig):
        raise TypeError(
            "report must be a ServiceReportConfig instance."
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


def print_service_report(
    summary: ServiceMonitoringSummary,
    report: ServiceReportConfig,
) -> None:
    """Print a service health report."""
    print(
        build_service_report(
            summary=summary,
            report=report,
        )
    )


def _build_record_lines(
    record: ServiceHealthRecord,
    report: ServiceReportConfig,
) -> list[str]:
    """Build report lines for one monitored service."""
    result = record.result

    lines = [
        f"{report.service_label}: {result.label}",
        f"{report.unit_label}: {result.service_name}",
        (
            f"{report.health_label}: "
            f"{record.health_status.value}"
        ),
    ]

    if result.load_state is not None:
        lines.append(
            f"{report.load_state_label}: {result.load_state}"
        )

    if result.active_state is not None:
        lines.append(
            f"{report.active_state_label}: {result.active_state}"
        )

    if result.sub_state is not None:
        lines.append(
            f"{report.sub_state_label}: {result.sub_state}"
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