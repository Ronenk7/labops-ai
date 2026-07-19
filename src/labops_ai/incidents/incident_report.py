"""Build and print human-readable incident management reports."""
from __future__ import annotations

from labops_ai.incidents.incident_config import IncidentReportConfig
from labops_ai.incidents.incident_models import (
    IncidentActionResult,
    IncidentActionType,
    IncidentRecord,
)
from labops_ai.incidents.incident_store import IncidentStoreState


def build_incident_report(
    actions: tuple[IncidentActionResult, ...],
    state: IncidentStoreState,
    report: IncidentReportConfig,
) -> str:
    """Build a complete incident management report."""
    _validate_report_dependencies(
        actions=actions,
        state=state,
        report=report,
    )

    action_counts = {
        action_type: sum(
            action.action_type is action_type
            for action in actions
        )
        for action_type in IncidentActionType
    }

    lines = [
        report.title,
        report.separator,
        f"{report.actions_label}: {len(actions)}",
        (
            f"{report.created_label}: "
            f"{action_counts[IncidentActionType.CREATED]}"
        ),
        (
            f"{report.updated_label}: "
            f"{action_counts[IncidentActionType.UPDATED]}"
        ),
        (
            f"{report.resolved_actions_label}: "
            f"{action_counts[IncidentActionType.RESOLVED]}"
        ),
        (
            f"{report.unchanged_label}: "
            f"{action_counts[IncidentActionType.UNCHANGED]}"
        ),
        (
            f"{report.active_count_label}: "
            f"{len(state.active_incidents)}"
        ),
        (
            f"{report.resolved_count_label}: "
            f"{len(state.resolved_incidents)}"
        ),
        report.separator,
    ]

    if not state.incidents:
        lines.extend(
            [
                report.no_incidents_message,
                report.separator,
            ]
        )
        return "\n".join(lines)

    for index, incident in enumerate(
        state.incidents,
        start=1,
    ):
        if index > 1:
            lines.append("")

        lines.extend(
            _build_incident_lines(
                incident=incident,
                index=index,
                report=report,
            )
        )

    lines.append(report.separator)

    return "\n".join(lines)


def print_incident_report(
    actions: tuple[IncidentActionResult, ...],
    state: IncidentStoreState,
    report: IncidentReportConfig,
) -> None:
    """Print a complete incident management report."""
    print(
        build_incident_report(
            actions=actions,
            state=state,
            report=report,
        )
    )


def _build_incident_lines(
    incident: IncidentRecord,
    index: int,
    report: IncidentReportConfig,
) -> list[str]:
    """Build report lines for one incident record."""
    lines = [
        f"{report.incident_label} {index}",
        f"{report.incident_id_label}: {incident.incident_id}",
        (
            f"{report.source_type_label}: "
            f"{incident.source_type.value}"
        ),
        f"{report.source_id_label}: {incident.source_id}",
        f"{report.source_label}: {incident.source_label}",
        f"{report.severity_label}: {incident.severity.value}",
        f"{report.status_label}: {incident.status.value}",
        f"{report.description_label}: {incident.description}",
        (
            f"{report.first_seen_label}: "
            f"{incident.first_seen_at.isoformat()}"
        ),
        (
            f"{report.last_seen_label}: "
            f"{incident.last_seen_at.isoformat()}"
        ),
        (
            f"{report.occurrences_label}: "
            f"{incident.occurrence_count}"
        ),
    ]

    if incident.resolved_at is not None:
        lines.append(
            f"{report.resolved_at_label}: "
            f"{incident.resolved_at.isoformat()}"
        )

    return lines


def _validate_report_dependencies(
    actions: object,
    state: object,
    report: object,
) -> None:
    """Validate all report dependencies."""
    if not isinstance(actions, tuple):
        raise TypeError(
            "actions must be a tuple of "
            "IncidentActionResult instances."
        )

    for action in actions:
        if not isinstance(action, IncidentActionResult):
            raise TypeError(
                "Every action must be an "
                "IncidentActionResult instance."
            )

    if not isinstance(state, IncidentStoreState):
        raise TypeError(
            "state must be an IncidentStoreState instance."
        )

    if not isinstance(report, IncidentReportConfig):
        raise TypeError(
            "report must be an IncidentReportConfig instance."
        )