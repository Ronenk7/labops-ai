"""Run the LabOps AI Linux process monitor."""
from labops_ai.processes import (
    ProcessMonitor,
    ProcessMonitorConfigLoader,
    PsutilProcessChecker,
    print_process_report,
)


def main() -> None:
    """Check configured Linux processes and print their report."""
    config = ProcessMonitorConfigLoader().load()
    checker = PsutilProcessChecker(
        collection_config=config.collection,
    )
    monitor = ProcessMonitor(
        config=config,
        checker=checker,
    )

    summary = monitor.run()

    print_process_report(
        summary=summary,
        report=config.report,
    )


if __name__ == "__main__":
    main()