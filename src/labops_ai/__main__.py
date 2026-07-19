"""Run all LabOps AI health monitoring components."""
from labops_ai.config import SystemHealthConfigLoader
from labops_ai.logs import (
    FileLogScanner,
    LogAnalyzer,
    LogAnalyzerConfigLoader,
    print_log_report,
)
from labops_ai.network import (
    ConnectivityConfigLoader,
    DnsConnectivityChecker,
    NetworkConnectivityMonitor,
    TcpConnectivityChecker,
    print_network_report,
)
from labops_ai.processes import (
    ProcessMonitor,
    ProcessMonitorConfigLoader,
    PsutilProcessChecker,
    print_process_report,
)
from labops_ai.services import (
    ServiceMonitor,
    ServiceMonitorConfigLoader,
    SystemctlServiceChecker,
    print_service_report,
)
from labops_ai.system_health import (
    SystemHealthMonitor,
    print_health_report,
)


def run_system_health() -> None:
    """Run system health monitoring and print its report."""
    config = SystemHealthConfigLoader().load()
    monitor = SystemHealthMonitor(config=config)

    metrics = monitor.collect_system_health()
    statuses = monitor.evaluate_system_health(metrics)
    overall_status = monitor.get_overall_status(statuses)

    print_health_report(
        metrics=metrics,
        statuses=statuses,
        overall_status=overall_status,
        report=config.report,
    )


def run_network_health() -> None:
    """Run network connectivity monitoring and print its report."""
    config = ConnectivityConfigLoader().load()

    dns_checker = DnsConnectivityChecker(
        config=config.dns_test,
    )
    tcp_checker = TcpConnectivityChecker(
        tcp_config=config.tcp_test,
        connection_settings=config.connection,
    )
    monitor = NetworkConnectivityMonitor(
        config=config,
        dns_checker=dns_checker,
        tcp_checker=tcp_checker,
    )

    summary = monitor.run()

    print_network_report(
        summary=summary,
        report=config.report,
    )


def run_service_health() -> None:
    """Run Linux service monitoring and print its report."""
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


def run_process_health() -> None:
    """Run Linux process monitoring and print its report."""
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


def run_log_analysis() -> None:
    """Run configured log analysis and print its report."""
    config = LogAnalyzerConfigLoader().load()
    scanner = FileLogScanner(config=config)
    analyzer = LogAnalyzer(
        config=config,
        scanner=scanner,
    )

    summary = analyzer.run()

    print_log_report(
        summary=summary,
        report=config.report,
    )


def main() -> None:
    """Run every currently supported LabOps AI check."""
    run_system_health()
    print()
    run_network_health()
    print()
    run_service_health()
    print()
    run_process_health()
    print()
    run_log_analysis()


if __name__ == "__main__":
    main()