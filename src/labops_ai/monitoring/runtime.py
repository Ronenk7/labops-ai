"""Reusable complete monitoring runtime for local and remote Agents."""
from labops_ai.config import (
    SystemHealthConfig,
    SystemHealthConfigLoader,
)
from labops_ai.diagnostics import (
    DiagnosticBundleConfigLoader,
    DiagnosticBundlePipeline,
    DiagnosticBundlePipelineResult,
    DiagnosticBundleWriter,
    DiagnosticSnapshotBuilder,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryConfigLoader,
    RunHistoryDatabase,
    RunHistoryEntry,
    RunHistoryRetentionPolicy,
    RunHistoryStore,
)
from labops_ai.incidents import (
    IncidentIdGenerator,
    IncidentManagementConfigLoader,
    IncidentManager,
    IncidentPipeline,
    IncidentProcessingSummary,
    IncidentSignalConfigLoader,
    IncidentSignalFactory,
    IncidentStoreState,
    JsonIncidentStore,
    print_incident_report,
)
from labops_ai.logs import (
    FileLogScanner,
    LogAnalysisSummary,
    LogAnalyzer,
    LogAnalyzerConfigLoader,
    print_log_report,
)
from labops_ai.network import (
    ConnectivityConfigLoader,
    DnsConnectivityChecker,
    NetworkConnectivityMonitor,
    NetworkConnectivitySummary,
    TcpConnectivityChecker,
    print_network_report,
)
from labops_ai.processes import (
    ProcessMonitor,
    ProcessMonitorConfigLoader,
    ProcessMonitoringSummary,
    PsutilProcessChecker,
    print_process_report,
)
from labops_ai.recovery import (
    JsonRecoveryStateStore,
    RecoveryConfigLoader,
    RecoveryManager,
    RecoveryRunSummary,
    SystemctlRecoveryExecutor,
    print_recovery_report,
)
from labops_ai.services import (
    ServiceMonitor,
    ServiceMonitorConfigLoader,
    ServiceMonitoringSummary,
    SystemctlServiceChecker,
    print_service_report,
)
from labops_ai.system_health import (
    SystemHealthMonitor,
    print_health_report,
)


SystemMetricValues = dict[str, float]
SystemMetricStatuses = dict[str, HealthStatus]
SystemHealthRunResult = tuple[
    SystemHealthConfig,
    SystemMetricValues,
    SystemMetricStatuses,
]


def run_system_health() -> SystemHealthRunResult:
    """Run system health monitoring and return its results."""
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

    return config, metrics, statuses


def run_network_health() -> NetworkConnectivitySummary:
    """Run network monitoring and return its summary."""
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

    return summary


def run_service_health() -> ServiceMonitoringSummary:
    """Run Linux service monitoring and return its summary."""
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

    return summary


def run_recovery_actions(
    service_summary: ServiceMonitoringSummary,
) -> RecoveryRunSummary:
    """Evaluate safe recovery actions for monitored services."""
    config = RecoveryConfigLoader().load()
    manager = RecoveryManager(
        config=config,
        executor=SystemctlRecoveryExecutor(),
        state_store=JsonRecoveryStateStore(),
    )

    summary = manager.run(service_summary)
    print_recovery_report(summary)

    return summary


def run_process_health() -> ProcessMonitoringSummary:
    """Run Linux process monitoring and return its summary."""
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

    return summary


def run_log_analysis() -> LogAnalysisSummary:
    """Run configured log analysis and return its summary."""
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

    return summary


def run_incident_management(
    *,
    system_config: SystemHealthConfig,
    system_metrics: SystemMetricValues,
    system_statuses: SystemMetricStatuses,
    network_summary: NetworkConnectivitySummary,
    service_summary: ServiceMonitoringSummary,
    process_summary: ProcessMonitoringSummary,
    log_summary: LogAnalysisSummary,
) -> IncidentProcessingSummary:
    """Process all monitoring output through incident management."""
    incident_config = IncidentManagementConfigLoader().load()
    signal_config = IncidentSignalConfigLoader().load()

    store = JsonIncidentStore(
        config=incident_config.storage
    )
    manager = IncidentManager(
        store=store,
        id_generator=IncidentIdGenerator(
            config=incident_config.identifier
        ),
    )
    pipeline = IncidentPipeline(
        signal_factory=IncidentSignalFactory(
            config=signal_config
        ),
        manager=manager,
    )

    summary = pipeline.run(
        system_metrics=system_metrics,
        system_statuses=system_statuses,
        system_metric_labels=(
            system_config.report.metric_labels
        ),
        network_summary=network_summary,
        service_summary=service_summary,
        process_summary=process_summary,
        log_summary=log_summary,
    )

    print_incident_report(
        actions=summary.actions,
        state=summary.state,
        report=incident_config.report,
    )

    return summary


def run_diagnostic_bundle(
    *,
    system_config: SystemHealthConfig,
    system_metrics: SystemMetricValues,
    system_statuses: SystemMetricStatuses,
    network_summary: NetworkConnectivitySummary,
    service_summary: ServiceMonitoringSummary,
    process_summary: ProcessMonitoringSummary,
    log_summary: LogAnalysisSummary,
    incident_state: IncidentStoreState,
) -> DiagnosticBundlePipelineResult:
    """Create one complete diagnostic ZIP bundle."""
    config = DiagnosticBundleConfigLoader().load()
    pipeline = DiagnosticBundlePipeline(
        snapshot_builder=DiagnosticSnapshotBuilder(),
        bundle_writer=DiagnosticBundleWriter(config=config),
    )

    result = pipeline.run(
        system_metrics=system_metrics,
        system_statuses=system_statuses,
        system_metric_labels=(
            system_config.report.metric_labels
        ),
        network_summary=network_summary,
        service_summary=service_summary,
        process_summary=process_summary,
        log_summary=log_summary,
        incident_state=incident_state,
    )

    print("LabOps AI - Diagnostic Bundle")
    print("-----------------------------------")
    print(f"Bundle ID: {result.bundle.bundle_id}")
    print(f"Archive: {result.bundle.archive_path}")
    print(
        "Artifacts: "
        f"{len(result.bundle.manifest.artifacts)}"
    )
    print(
        "Overall status: "
        f"{result.snapshot.overall_status.value}"
    )
    print("-----------------------------------")

    return result


def save_run_history(
    result: DiagnosticBundlePipelineResult,
) -> RunHistoryEntry:
    """Persist one diagnostic run in SQLite history."""
    config = RunHistoryConfigLoader().load()

    database = RunHistoryDatabase(
        config=config.storage,
    )
    retention_policy = RunHistoryRetentionPolicy(
        config=config.retention,
    )
    store = RunHistoryStore(
        database=database,
        retention_policy=retention_policy,
    )

    entry = store.save(
        result.snapshot,
        bundle_id=result.bundle.bundle_id,
        archive_path=result.bundle.archive_path,
    )

    print("LabOps AI - Run History")
    print("-----------------------------------")
    print(f"Run ID: {entry.run_id}")
    print(f"Generated at: {entry.generated_at.isoformat()}")
    print(f"Host: {entry.host_name}")
    print(f"Overall status: {entry.overall_status.value}")
    print("-----------------------------------")

    return entry


def run_complete_monitoring() -> RunHistoryEntry:
    """Run and persist one complete monitoring cycle."""
    (
        system_config,
        system_metrics,
        system_statuses,
    ) = run_system_health()

    print()
    network_summary = run_network_health()

    print()
    service_summary = run_service_health()

    print()
    run_recovery_actions(service_summary)

    print()
    process_summary = run_process_health()

    print()
    log_summary = run_log_analysis()

    print()
    incident_summary = run_incident_management(
        system_config=system_config,
        system_metrics=system_metrics,
        system_statuses=system_statuses,
        network_summary=network_summary,
        service_summary=service_summary,
        process_summary=process_summary,
        log_summary=log_summary,
    )

    print()
    diagnostic_result = run_diagnostic_bundle(
        system_config=system_config,
        system_metrics=system_metrics,
        system_statuses=system_statuses,
        network_summary=network_summary,
        service_summary=service_summary,
        process_summary=process_summary,
        log_summary=log_summary,
        incident_state=incident_summary.state,
    )

    print()
    return save_run_history(diagnostic_result)
