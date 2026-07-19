"""Build JSON and text reports from diagnostic snapshots."""
from __future__ import annotations

import json
from typing import Any

from labops_ai.diagnostics.diagnostic_snapshot import (
    DiagnosticSnapshot,
)


_DIAGNOSTIC_REPORT_SCHEMA_VERSION = 1
_TEXT_REPORT_TITLE = "LabOps AI Diagnostic Report"
_TEXT_REPORT_SEPARATOR = "=" * len(_TEXT_REPORT_TITLE)
_SECTION_SEPARATOR = "-" * 40


def build_diagnostic_payload(
    snapshot: DiagnosticSnapshot,
) -> dict[str, Any]:
    """Convert a diagnostic snapshot into a JSON-compatible object."""
    _validate_snapshot(snapshot)

    return {
        "schema_version": _DIAGNOSTIC_REPORT_SCHEMA_VERSION,
        "generated_at": snapshot.generated_at.isoformat(),
        "host_name": snapshot.host_name,
        "overall_status": snapshot.overall_status.value,
        "summary": {
            "active_incidents": snapshot.active_incident_count,
            "resolved_incidents": (
                snapshot.resolved_incident_count
            ),
            "system_status": (
                snapshot.system_overall_status.value
            ),
            "network_status": (
                snapshot.network_overall_status.value
            ),
            "service_status": (
                snapshot.service_overall_status.value
            ),
            "process_status": (
                snapshot.process_overall_status.value
            ),
            "log_status": snapshot.log_overall_status.value,
        },
        "system": {
            "overall_status": (
                snapshot.system_overall_status.value
            ),
            "metrics": [
                {
                    "metric_name": metric.metric_name,
                    "label": metric.label,
                    "value_percent": metric.value_percent,
                    "health_status": (
                        metric.health_status.value
                    ),
                }
                for metric in snapshot.system_metrics
            ],
        },
        "network": {
            "overall_status": (
                snapshot.network_overall_status.value
            ),
            "checks": [
                {
                    "check_type": check.check_type.value,
                    "target": check.target,
                    "check_status": check.check_status.value,
                    "health_status": (
                        check.health_status.value
                    ),
                    "latency_ms": check.latency_ms,
                    "resolved_address": (
                        check.resolved_address
                    ),
                    "failure_reason": (
                        check.failure_reason.value
                        if check.failure_reason is not None
                        else None
                    ),
                    "error_message": check.error_message,
                }
                for check in snapshot.network_checks
            ],
        },
        "services": {
            "overall_status": (
                snapshot.service_overall_status.value
            ),
            "records": [
                {
                    "service_name": service.service_name,
                    "label": service.label,
                    "check_status": (
                        service.check_status.value
                    ),
                    "health_status": (
                        service.health_status.value
                    ),
                    "load_state": service.load_state,
                    "active_state": service.active_state,
                    "sub_state": service.sub_state,
                    "failure_reason": (
                        service.failure_reason.value
                        if service.failure_reason is not None
                        else None
                    ),
                    "error_message": service.error_message,
                }
                for service in snapshot.services
            ],
        },
        "processes": {
            "overall_status": (
                snapshot.process_overall_status.value
            ),
            "records": [
                {
                    "process_name": process.process_name,
                    "label": process.label,
                    "required": process.required,
                    "check_status": (
                        process.check_status.value
                    ),
                    "health_status": (
                        process.health_status.value
                    ),
                    "instance_count": process.instance_count,
                    "pids": list(process.pids),
                    "total_cpu_percent": (
                        process.total_cpu_percent
                    ),
                    "total_memory_mb": (
                        process.total_memory_mb
                    ),
                    "longest_runtime_seconds": (
                        process.longest_runtime_seconds
                    ),
                    "failure_reason": (
                        process.failure_reason.value
                        if process.failure_reason is not None
                        else None
                    ),
                    "error_message": process.error_message,
                }
                for process in snapshot.processes
            ],
        },
        "logs": {
            "overall_status": (
                snapshot.log_overall_status.value
            ),
            "records": [
                {
                    "source_id": log.source_id,
                    "label": log.label,
                    "path": log.path,
                    "required": log.required,
                    "scan_status": log.scan_status.value,
                    "health_status": (
                        log.health_status.value
                    ),
                    "total_lines_scanned": (
                        log.total_lines_scanned
                    ),
                    "match_count": log.match_count,
                    "failure_reason": (
                        log.failure_reason.value
                        if log.failure_reason is not None
                        else None
                    ),
                    "error_message": log.error_message,
                }
                for log in snapshot.logs
            ],
        },
        "incidents": {
            "active_count": snapshot.active_incident_count,
            "resolved_count": (
                snapshot.resolved_incident_count
            ),
            "records": [
                {
                    "incident_id": incident.incident_id,
                    "source_type": incident.source_type.value,
                    "source_id": incident.source_id,
                    "source_label": incident.source_label,
                    "severity": incident.severity.value,
                    "status": incident.status.value,
                    "description": incident.description,
                    "first_seen_at": (
                        incident.first_seen_at.isoformat()
                    ),
                    "last_seen_at": (
                        incident.last_seen_at.isoformat()
                    ),
                    "occurrence_count": (
                        incident.occurrence_count
                    ),
                    "resolved_at": (
                        incident.resolved_at.isoformat()
                        if incident.resolved_at is not None
                        else None
                    ),
                }
                for incident in snapshot.incidents
            ],
        },
    }


def build_diagnostic_json(
    snapshot: DiagnosticSnapshot,
) -> str:
    """Build a deterministic formatted JSON diagnostic report."""
    payload = build_diagnostic_payload(snapshot)

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def build_diagnostic_text(
    snapshot: DiagnosticSnapshot,
) -> str:
    """Build a human-readable diagnostic report."""
    _validate_snapshot(snapshot)

    lines = [
        _TEXT_REPORT_TITLE,
        _TEXT_REPORT_SEPARATOR,
        f"Generated at: {snapshot.generated_at.isoformat()}",
        f"Host: {snapshot.host_name}",
        f"Overall status: {snapshot.overall_status.value}",
        (
            "Active incidents: "
            f"{snapshot.active_incident_count}"
        ),
        (
            "Resolved incidents: "
            f"{snapshot.resolved_incident_count}"
        ),
        "",
    ]

    _append_system_section(lines, snapshot)
    _append_network_section(lines, snapshot)
    _append_service_section(lines, snapshot)
    _append_process_section(lines, snapshot)
    _append_log_section(lines, snapshot)
    _append_incident_section(lines, snapshot)

    return "\n".join(lines) + "\n"


def _append_system_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append system health details."""
    lines.extend(
        [
            "SYSTEM HEALTH",
            _SECTION_SEPARATOR,
            (
                "Overall status: "
                f"{snapshot.system_overall_status.value}"
            ),
        ]
    )

    for metric in snapshot.system_metrics:
        lines.append(
            f"{metric.label} ({metric.metric_name}): "
            f"{metric.value_percent:.2f}% "
            f"[{metric.health_status.value}]"
        )

    lines.append("")


def _append_network_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append network check details."""
    lines.extend(
        [
            "NETWORK HEALTH",
            _SECTION_SEPARATOR,
            (
                "Overall status: "
                f"{snapshot.network_overall_status.value}"
            ),
        ]
    )

    for index, check in enumerate(
        snapshot.network_checks,
        start=1,
    ):
        if index > 1:
            lines.append("")

        lines.extend(
            [
                (
                    f"{check.check_type.value}: "
                    f"{check.check_status.value} "
                    f"[{check.health_status.value}]"
                ),
                f"Target: {check.target}",
            ]
        )

        if check.latency_ms is not None:
            lines.append(
                f"Latency: {check.latency_ms:.2f} ms"
            )

        if check.resolved_address is not None:
            lines.append(
                f"Resolved address: {check.resolved_address}"
            )

        _append_failure_details(
            lines=lines,
            failure_reason=(
                check.failure_reason.value
                if check.failure_reason is not None
                else None
            ),
            error_message=check.error_message,
        )

    lines.append("")


def _append_service_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append Linux service details."""
    lines.extend(
        [
            "SERVICE HEALTH",
            _SECTION_SEPARATOR,
            (
                "Overall status: "
                f"{snapshot.service_overall_status.value}"
            ),
        ]
    )

    for index, service in enumerate(
        snapshot.services,
        start=1,
    ):
        if index > 1:
            lines.append("")

        lines.extend(
            [
                f"Service: {service.label}",
                f"Unit: {service.service_name}",
                (
                    "Check status: "
                    f"{service.check_status.value}"
                ),
                f"Health: {service.health_status.value}",
            ]
        )

        _append_optional_line(
            lines,
            "Load state",
            service.load_state,
        )
        _append_optional_line(
            lines,
            "Active state",
            service.active_state,
        )
        _append_optional_line(
            lines,
            "Sub state",
            service.sub_state,
        )

        _append_failure_details(
            lines=lines,
            failure_reason=(
                service.failure_reason.value
                if service.failure_reason is not None
                else None
            ),
            error_message=service.error_message,
        )

    lines.append("")


def _append_process_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append process monitoring details."""
    lines.extend(
        [
            "PROCESS HEALTH",
            _SECTION_SEPARATOR,
            (
                "Overall status: "
                f"{snapshot.process_overall_status.value}"
            ),
        ]
    )

    for index, process in enumerate(
        snapshot.processes,
        start=1,
    ):
        if index > 1:
            lines.append("")

        pids = (
            ", ".join(str(pid) for pid in process.pids)
            if process.pids
            else "None"
        )

        lines.extend(
            [
                f"Process: {process.label}",
                f"Name: {process.process_name}",
                (
                    "Required: "
                    f"{'Yes' if process.required else 'No'}"
                ),
                (
                    "Check status: "
                    f"{process.check_status.value}"
                ),
                f"Health: {process.health_status.value}",
                f"Instances: {process.instance_count}",
                f"PIDs: {pids}",
                (
                    "Total CPU: "
                    f"{process.total_cpu_percent:.2f}%"
                ),
                (
                    "Total memory: "
                    f"{process.total_memory_mb:.2f} MB"
                ),
                (
                    "Longest runtime: "
                    f"{process.longest_runtime_seconds:.2f} "
                    "seconds"
                ),
            ]
        )

        _append_failure_details(
            lines=lines,
            failure_reason=(
                process.failure_reason.value
                if process.failure_reason is not None
                else None
            ),
            error_message=process.error_message,
        )

    lines.append("")


def _append_log_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append log analysis details."""
    lines.extend(
        [
            "LOG ANALYSIS",
            _SECTION_SEPARATOR,
            (
                "Overall status: "
                f"{snapshot.log_overall_status.value}"
            ),
        ]
    )

    for index, log in enumerate(
        snapshot.logs,
        start=1,
    ):
        if index > 1:
            lines.append("")

        lines.extend(
            [
                f"Log source: {log.label}",
                f"Source ID: {log.source_id}",
                f"Path: {log.path}",
                (
                    "Required: "
                    f"{'Yes' if log.required else 'No'}"
                ),
                f"Scan status: {log.scan_status.value}",
                f"Health: {log.health_status.value}",
                (
                    "Lines scanned: "
                    f"{log.total_lines_scanned}"
                ),
                f"Matches: {log.match_count}",
            ]
        )

        _append_failure_details(
            lines=lines,
            failure_reason=(
                log.failure_reason.value
                if log.failure_reason is not None
                else None
            ),
            error_message=log.error_message,
        )

    lines.append("")


def _append_incident_section(
    lines: list[str],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Append persisted incident details."""
    lines.extend(
        [
            "INCIDENTS",
            _SECTION_SEPARATOR,
            (
                "Active incidents: "
                f"{snapshot.active_incident_count}"
            ),
            (
                "Resolved incidents: "
                f"{snapshot.resolved_incident_count}"
            ),
        ]
    )

    if not snapshot.incidents:
        lines.append("No incidents are recorded.")
        return

    for index, incident in enumerate(
        snapshot.incidents,
        start=1,
    ):
        lines.append("")
        lines.extend(
            [
                f"Incident {index}",
                f"Incident ID: {incident.incident_id}",
                (
                    "Source type: "
                    f"{incident.source_type.value}"
                ),
                f"Source ID: {incident.source_id}",
                f"Source: {incident.source_label}",
                f"Severity: {incident.severity.value}",
                f"Status: {incident.status.value}",
                f"Description: {incident.description}",
                (
                    "First seen: "
                    f"{incident.first_seen_at.isoformat()}"
                ),
                (
                    "Last seen: "
                    f"{incident.last_seen_at.isoformat()}"
                ),
                (
                    "Occurrences: "
                    f"{incident.occurrence_count}"
                ),
            ]
        )

        if incident.resolved_at is not None:
            lines.append(
                "Resolved at: "
                f"{incident.resolved_at.isoformat()}"
            )


def _append_failure_details(
    *,
    lines: list[str],
    failure_reason: str | None,
    error_message: str | None,
) -> None:
    """Append optional normalized failure information."""
    _append_optional_line(
        lines,
        "Failure reason",
        failure_reason,
    )
    _append_optional_line(
        lines,
        "Error",
        error_message,
    )


def _append_optional_line(
    lines: list[str],
    label: str,
    value: str | None,
) -> None:
    """Append one line only when its value exists."""
    if value is not None:
        lines.append(f"{label}: {value}")


def _validate_snapshot(snapshot: object) -> None:
    """Validate the report input dependency."""
    if not isinstance(snapshot, DiagnosticSnapshot):
        raise TypeError(
            "snapshot must be a DiagnosticSnapshot instance."
        )