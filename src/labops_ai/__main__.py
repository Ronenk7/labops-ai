"""Run one complete LabOps AI monitoring cycle."""

from labops_ai.monitoring.runtime import (
    run_complete_monitoring,
    run_diagnostic_bundle,
    run_incident_management,
    run_log_analysis,
    run_network_health,
    run_process_health,
    run_recovery_actions,
    run_service_health,
    run_system_health,
    save_run_history,
)


def main() -> None:
    """Execute one complete monitoring cycle."""
    run_complete_monitoring()


if __name__ == "__main__":
    main()
