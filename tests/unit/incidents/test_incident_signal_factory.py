"""Unit tests for incident signal creation."""
from __future__ import annotations

from datetime import datetime

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentSignalConfigLoader,
    IncidentSignalFactory,
    IncidentSourceType,
)
from labops_ai.logs.log_config import LogSourceConfig
from labops_ai.logs.log_monitor import (
    LogAnalysisSummary,
    LogHealthRecord,
)
from labops_ai.logs.log_result import (
    LogFailureReason,
    LogMatch,
    LogScanStatus,
    LogSourceResult,
)
from labops_ai.network.connectivity_monitor import (
    NetworkConnectivitySummary,
)
from labops_ai.network.connectivity_result import (
    ConnectivityCheckResult,
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.processes.process_config import (
    ProcessCpuThresholds,
    ProcessMemoryThresholds,
    ProcessTargetConfig,
)
from labops_ai.processes.process_monitor import (
    ProcessHealthRecord,
    ProcessMonitoringSummary,
)
from labops_ai.processes.process_result import (
    ProcessCheckResult,
    ProcessCheckStatus,
    ProcessInstanceSnapshot,
)
from labops_ai.services.service_monitor import (
    ServiceHealthRecord,
    ServiceMonitoringSummary,
)
from labops_ai.services.service_result import (
    ServiceCheckResult,
    ServiceCheckStatus,
    ServiceFailureReason,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_signal_factory_cases.json"
)
OBSERVED_AT = datetime.fromisoformat(CASES["observed_at"])


def build_factory() -> IncidentSignalFactory:
    """Build a signal factory from project configuration."""
    return IncidentSignalFactory(
        config=IncidentSignalConfigLoader().load()
    )


def build_network_summary() -> NetworkConnectivitySummary:
    """Build a controlled network monitoring summary."""
    values = CASES["network"]

    return NetworkConnectivitySummary(
        dns_result=ConnectivityCheckResult(
            check_type=ConnectivityCheckType.DNS,
            status=ConnectivityCheckStatus.PASSED,
            target=values["dns_target"],
            latency_ms=values["dns_latency_ms"],
            resolved_address="104.16.124.96",
        ),
        dns_status=HealthStatus.HEALTHY,
        tcp_result=ConnectivityCheckResult(
            check_type=ConnectivityCheckType.TCP,
            status=ConnectivityCheckStatus.FAILED,
            target=values["tcp_target"],
            failure_reason=ConnectivityFailureReason.TIMEOUT,
            error_message=values["tcp_error"],
        ),
        tcp_status=HealthStatus.CRITICAL,
        overall_status=HealthStatus.CRITICAL,
    )


def build_service_summary() -> ServiceMonitoringSummary:
    """Build a controlled service monitoring summary."""
    values = CASES["service"]

    active_result = ServiceCheckResult(
        service_name=values["active_name"],
        label=values["active_label"],
        status=ServiceCheckStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="running",
    )
    error_result = ServiceCheckResult(
        service_name=values["error_name"],
        label=values["error_label"],
        status=ServiceCheckStatus.CHECK_ERROR,
        failure_reason=ServiceFailureReason.TIMEOUT,
        error_message=values["error_message"],
    )

    return ServiceMonitoringSummary(
        records=(
            ServiceHealthRecord(
                result=active_result,
                health_status=HealthStatus.HEALTHY,
            ),
            ServiceHealthRecord(
                result=error_result,
                health_status=HealthStatus.CRITICAL,
            ),
        ),
        overall_status=HealthStatus.CRITICAL,
    )


def build_process_summary() -> ProcessMonitoringSummary:
    """Build a controlled process monitoring summary."""
    values = CASES["process"]
    cpu_thresholds = ProcessCpuThresholds(
        warning=70,
        critical=90,
    )
    memory_thresholds = ProcessMemoryThresholds(
        warning=400,
        critical=600,
    )

    running_target = ProcessTargetConfig(
        process_name=values["running_name"],
        label=values["running_label"],
        required=True,
        cpu_thresholds_percent=cpu_thresholds,
        memory_thresholds_mb=memory_thresholds,
    )
    missing_target = ProcessTargetConfig(
        process_name=values["missing_name"],
        label=values["missing_label"],
        required=True,
        cpu_thresholds_percent=cpu_thresholds,
        memory_thresholds_mb=memory_thresholds,
    )

    running_result = ProcessCheckResult(
        process_name=values["running_name"],
        label=values["running_label"],
        required=True,
        status=ProcessCheckStatus.RUNNING,
        instances=(
            ProcessInstanceSnapshot(
                pid=100,
                cpu_percent=75.5,
                memory_mb=450.25,
                runtime_seconds=1000,
            ),
        ),
    )
    missing_result = ProcessCheckResult(
        process_name=values["missing_name"],
        label=values["missing_label"],
        required=True,
        status=ProcessCheckStatus.NOT_RUNNING,
    )

    return ProcessMonitoringSummary(
        records=(
            ProcessHealthRecord(
                target=running_target,
                result=running_result,
                health_status=HealthStatus.WARNING,
            ),
            ProcessHealthRecord(
                target=missing_target,
                result=missing_result,
                health_status=HealthStatus.CRITICAL,
            ),
        ),
        overall_status=HealthStatus.CRITICAL,
    )


def build_log_summary() -> LogAnalysisSummary:
    """Build a controlled log analysis summary."""
    values = CASES["log"]

    analyzed_source = LogSourceConfig(
        source_id=values["analyzed_id"],
        label=values["analyzed_label"],
        path="logs/application.log",
        required=True,
    )
    error_source = LogSourceConfig(
        source_id=values["error_id"],
        label=values["error_label"],
        path="/var/log/syslog",
        required=False,
    )

    analyzed_result = LogSourceResult(
        source_id=values["analyzed_id"],
        label=values["analyzed_label"],
        path="logs/application.log",
        required=True,
        status=LogScanStatus.ANALYZED,
        total_lines_scanned=10,
        matches=(
            LogMatch(
                rule_id="timeout",
                rule_label="Timeout event",
                severity=HealthStatus.WARNING,
                line_number=5,
                content="Request TIMEOUT",
            ),
        ),
    )
    error_result = LogSourceResult(
        source_id=values["error_id"],
        label=values["error_label"],
        path="/var/log/syslog",
        required=False,
        status=LogScanStatus.CHECK_ERROR,
        total_lines_scanned=0,
        failure_reason=LogFailureReason.FILE_NOT_FOUND,
        error_message=values["error_message"],
    )

    return LogAnalysisSummary(
        records=(
            LogHealthRecord(
                source=analyzed_source,
                result=analyzed_result,
                health_status=HealthStatus.WARNING,
            ),
            LogHealthRecord(
                source=error_source,
                result=error_result,
                health_status=HealthStatus.WARNING,
            ),
        ),
        overall_status=HealthStatus.WARNING,
    )


class TestIncidentSignalFactory:
    """Test conversion from monitoring results to signals."""

    def test_creates_system_signals(self) -> None:
        values = CASES["system"]

        signals = build_factory().from_system(
            metrics=values["metrics"],
            statuses={
                name: HealthStatus(status)
                for name, status in values["statuses"].items()
            },
            metric_labels=values["labels"],
            observed_at=OBSERVED_AT,
        )

        assert len(signals) == 3
        assert [
            signal.description
            for signal in signals
        ] == values["expected_descriptions"]
        assert signals[0].source_type is IncidentSourceType.SYSTEM

    def test_creates_network_signals(self) -> None:
        signals = build_factory().from_network(
            summary=build_network_summary(),
            observed_at=OBSERVED_AT,
        )

        assert signals[0].source_id == (
            "dns:www.cloudflare.com"
        )
        assert signals[1].source_id == "tcp:1.1.1.1:443"
        assert signals[0].description == (
            CASES["network"]["expected_dns_description"]
        )
        assert signals[1].description == (
            CASES["network"]["expected_tcp_description"]
        )

    def test_creates_service_signals(self) -> None:
        signals = build_factory().from_services(
            summary=build_service_summary(),
            observed_at=OBSERVED_AT,
        )

        assert signals[0].description == (
            CASES["service"]["expected_active_description"]
        )
        assert signals[1].description == (
            CASES["service"]["expected_error_description"]
        )

    def test_creates_process_signals(self) -> None:
        signals = build_factory().from_processes(
            summary=build_process_summary(),
            observed_at=OBSERVED_AT,
        )

        assert signals[0].description == (
            CASES["process"][
                "expected_running_description"
            ]
        )
        assert signals[1].description == (
            CASES["process"][
                "expected_missing_description"
            ]
        )

    def test_creates_log_signals(self) -> None:
        signals = build_factory().from_logs(
            summary=build_log_summary(),
            observed_at=OBSERVED_AT,
        )

        assert signals[0].description == (
            CASES["log"][
                "expected_analyzed_description"
            ]
        )
        assert signals[1].description == (
            CASES["log"]["expected_error_description"]
        )

    def test_creates_all_signals_in_domain_order(self) -> None:
        system = CASES["system"]

        signals = build_factory().from_all(
            system_metrics=system["metrics"],
            system_statuses={
                name: HealthStatus(status)
                for name, status in system["statuses"].items()
            },
            system_metric_labels=system["labels"],
            network_summary=build_network_summary(),
            service_summary=build_service_summary(),
            process_summary=build_process_summary(),
            log_summary=build_log_summary(),
            observed_at=OBSERVED_AT,
        )

        assert len(signals) == 11
        assert [
            signal.source_type
            for signal in signals
        ] == [
            IncidentSourceType.SYSTEM,
            IncidentSourceType.SYSTEM,
            IncidentSourceType.SYSTEM,
            IncidentSourceType.NETWORK,
            IncidentSourceType.NETWORK,
            IncidentSourceType.SERVICE,
            IncidentSourceType.SERVICE,
            IncidentSourceType.PROCESS,
            IncidentSourceType.PROCESS,
            IncidentSourceType.LOG,
            IncidentSourceType.LOG,
        ]

    def test_rejects_mismatched_system_keys(self) -> None:
        with pytest.raises(
            ValueError,
            match="same keys",
        ):
            build_factory().from_system(
                metrics={"cpu_percent": 10.0},
                statuses={
                    "memory_percent": HealthStatus.HEALTHY
                },
                metric_labels={"cpu_percent": "CPU usage"},
                observed_at=OBSERVED_AT,
            )

    def test_rejects_invalid_network_summary(self) -> None:
        with pytest.raises(
            TypeError,
            match="NetworkConnectivitySummary",
        ):
            build_factory().from_network(
                summary=object(),
                observed_at=OBSERVED_AT,
            )

    def test_rejects_observation_without_timezone(self) -> None:
        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            build_factory().from_network(
                summary=build_network_summary(),
                observed_at=datetime(2026, 7, 19, 10, 30),
            )