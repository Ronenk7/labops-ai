"""Unit tests for log analysis reports."""
from __future__ import annotations

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.logs import (
    LogAnalysisSummary,
    LogFailureReason,
    LogHealthRecord,
    LogMatch,
    LogReportConfig,
    LogScanStatus,
    LogSourceConfig,
    LogSourceResult,
    build_log_report,
    print_log_report,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CONFIG_CASES = load_test_fixture(
    "logs/log_config_cases.json"
)
REPORT_CASES = load_test_fixture(
    "logs/log_report_cases.json"
)
REPORT = LogReportConfig(
    **CONFIG_CASES["valid_report"]
)


def build_summary() -> LogAnalysisSummary:
    """Build a controlled log analysis summary."""
    application_source = LogSourceConfig(
        source_id="application",
        label="Application Log",
        path="logs/application.log",
        required=True,
    )
    system_source = LogSourceConfig(
        source_id="system",
        label="Optional System Log",
        path="/var/log/syslog",
        required=False,
    )

    application_result = LogSourceResult(
        source_id="application",
        label="Application Log",
        path="logs/application.log",
        required=True,
        status=LogScanStatus.ANALYZED,
        total_lines_scanned=3,
        matches=(
            LogMatch(
                rule_id="timeout",
                rule_label="Timeout event",
                severity=HealthStatus.WARNING,
                line_number=2,
                content="WARNING Request TIMEOUT",
            ),
            LogMatch(
                rule_id="error",
                rule_label="Error event",
                severity=HealthStatus.CRITICAL,
                line_number=3,
                content="ERROR Connection refused",
            ),
        ),
    )
    system_result = LogSourceResult(
        source_id="system",
        label="Optional System Log",
        path="/var/log/syslog",
        required=False,
        status=LogScanStatus.CHECK_ERROR,
        total_lines_scanned=0,
        failure_reason=LogFailureReason.FILE_NOT_FOUND,
        error_message="Log file was not found.",
    )

    return LogAnalysisSummary(
        records=(
            LogHealthRecord(
                source=application_source,
                result=application_result,
                health_status=HealthStatus.CRITICAL,
            ),
            LogHealthRecord(
                source=system_source,
                result=system_result,
                health_status=HealthStatus.WARNING,
            ),
        ),
        overall_status=HealthStatus.CRITICAL,
    )


class TestBuildLogReport:
    """Test log analysis report construction."""

    def test_builds_complete_log_report(self) -> None:
        actual_report = build_log_report(
            summary=build_summary(),
            report=REPORT,
        )

        assert (
            actual_report
            == REPORT_CASES["expected_report"]
        )

    def test_rejects_invalid_summary(self) -> None:
        with pytest.raises(
            TypeError,
            match="LogAnalysisSummary",
        ):
            build_log_report(
                summary=object(),
                report=REPORT,
            )


class TestPrintLogReport:
    """Test log report printing."""

    def test_prints_complete_log_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        print_log_report(
            summary=build_summary(),
            report=REPORT,
        )

        captured = capsys.readouterr()

        assert (
            captured.out
            == f'{REPORT_CASES["expected_report"]}\n'
        )
        assert captured.err == ""