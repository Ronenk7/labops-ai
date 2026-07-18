"""Run the LabOps AI Linux service monitor."""
from labops_ai.services import (
    ServiceMonitor,
    ServiceMonitorConfigLoader,
    SystemctlServiceChecker,
    print_service_report,
)


def main() -> None:
    """Check configured Linux services and print their report."""
    config = ServiceMonitorConfigLoader().load()
    checker = SystemctlServiceChecker(
        command_config=config.command,
    )
    monitor = ServiceMonitor(
        config=config,
        checker=checker,
    )

    summary = monitor.run()

    print_service_report(
        summary=summary,
        report=config.report,
    )


if __name__ == "__main__":
    main()