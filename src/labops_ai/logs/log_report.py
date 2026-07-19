"""Build human-readable log analysis reports."""
from __future__ import annotations

from labops_ai.logs.log_config import LogReportConfig
from labops_ai.logs.log_monitor import (
    LogAnalysisSummary,
    LogHealthRecord,
)


def build_log_report(
    summary: LogAnalysisSummary,
    report: LogReportConfig,
) -> str:
    """Build a complete log analysis report."""
    if not isinstance(summary, LogAnalysisSummary):
        raise TypeError(
            "summary must be a LogAnalysisSummary instance."
        )

    if not isinstance(report, LogReportConfig):
        raise TypeError(
            "report must be a LogReportConfig instance."
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


def print_log_report(
    summary: LogAnalysisSummary,
    report: LogReportConfig,
) -> None:
    """Print a complete log analysis report."""
    print(
        build_log_report(
            summary=summary,
            report=report,
        )
    )


def _build_record_lines(
    record: LogHealthRecord,
    report: LogReportConfig,
) -> list[str]:
    """Build report lines for one log source."""
    result = record.result
    required_value = (
        report.yes_value
        if result.required
        else report.no_value
    )

    lines = [
        f"{report.source_label}: {result.label}",
        f"{report.source_id_label}: {result.source_id}",
        f"{report.path_label}: {result.path}",
        f"{report.required_label}: {required_value}",
        (
            f"{report.scan_status_label}: "
            f"{result.status.value}"
        ),
        (
            f"{report.health_label}: "
            f"{record.health_status.value}"
        ),
        (
            f"{report.lines_scanned_label}: "
            f"{result.total_lines_scanned}"
        ),
        f"{report.matches_label}: {len(result.matches)}",
    ]

    for index, match in enumerate(
        result.matches,
        start=1,
    ):
        lines.extend(
            [
                f"{report.match_label} {index}:",
                f"{report.rule_label}: {match.rule_label}",
                (
                    f"{report.severity_label}: "
                    f"{match.severity.value}"
                ),
                (
                    f"{report.line_number_label}: "
                    f"{match.line_number}"
                ),
                f"{report.content_label}: {match.content}",
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