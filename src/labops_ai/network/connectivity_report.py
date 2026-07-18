"""Build and print human-readable network connectivity reports."""
from __future__ import annotations

from labops_ai.health_status import HealthStatus
from labops_ai.network.connectivity_config import NetworkReportConfig
from labops_ai.network.connectivity_monitor import NetworkConnectivitySummary
from labops_ai.network.connectivity_result import ConnectivityCheckResult


def build_network_report(
    summary: NetworkConnectivitySummary,
    report: NetworkReportConfig,
) -> str:
    """Build a network connectivity report from an evaluated summary."""
    if not isinstance(summary, NetworkConnectivitySummary):
        raise TypeError(
            "summary must be a NetworkConnectivitySummary instance."
        )

    if not isinstance(report, NetworkReportConfig):
        raise TypeError("report must be a NetworkReportConfig instance.")

    lines = [
        report.title,
        report.separator,
        *_build_check_lines(
            label=report.dns_label,
            status=summary.dns_status,
            result=summary.dns_result,
            report=report,
        ),
        "",
        *_build_check_lines(
            label=report.tcp_label,
            status=summary.tcp_status,
            result=summary.tcp_result,
            report=report,
        ),
        report.separator,
        f"{report.overall_label}: {summary.overall_status.value}",
    ]

    return "\n".join(lines)


def print_network_report(
    summary: NetworkConnectivitySummary,
    report: NetworkReportConfig,
) -> None:
    """Print a human-readable network connectivity report."""
    print(build_network_report(summary=summary, report=report))


def _build_check_lines(
    label: str,
    status: HealthStatus,
    result: ConnectivityCheckResult,
    report: NetworkReportConfig,
) -> list[str]:
    """Build report lines for one connectivity check."""
    lines = [
        f"{label}: {status.value}",
        f"{report.target_label}: {result.target}",
    ]

    if result.resolved_address is not None:
        lines.append(
            f"{report.resolved_address_label}: "
            f"{result.resolved_address}"
        )

    if result.latency_ms is not None:
        lines.append(
            f"{report.latency_label}: "
            f"{result.latency_ms:.2f} "
            f"{report.latency_unit}"
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