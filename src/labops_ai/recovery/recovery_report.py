"""Build and print recovery action reports."""
from __future__ import annotations

from labops_ai.recovery.recovery_models import (
    RecoveryRunSummary,
)


def build_recovery_report(
    summary: RecoveryRunSummary,
) -> str:
    """Build a readable recovery action report."""
    if not isinstance(summary, RecoveryRunSummary):
        raise TypeError(
            "summary must be a RecoveryRunSummary."
        )

    lines = [
        "LabOps AI - Recovery Actions",
        "-----------------------------------",
        f"Decisions: {len(summary.results)}",
        f"Attempted: {summary.attempted_count}",
        f"Successful: {summary.successful_count}",
        f"Dry run: {summary.dry_run_count}",
    ]

    for result in summary.results:
        lines.extend(
            [
                "",
                f"Action: {result.action_id}",
                f"Unit: {result.unit}",
                f"Health: {result.health_status.value}",
                f"Outcome: {result.outcome.value}",
                f"Details: {result.details}",
            ]
        )

    lines.append("-----------------------------------")
    return "\n".join(lines)


def print_recovery_report(
    summary: RecoveryRunSummary,
) -> None:
    """Print one recovery action report."""
    print(build_recovery_report(summary))
