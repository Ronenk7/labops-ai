"""Unit tests for log analysis health evaluation."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.logs import (
    LogAnalyzer,
    LogAnalyzerConfig,
    LogCollectionConfig,
    LogFailureReason,
    LogMatch,
    LogReportConfig,
    LogRuleConfig,
    LogScanStatus,
    LogSourceConfig,
    LogSourceResult,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "logs/log_monitor_cases.json"
)
CONFIG_CASES = load_test_fixture(
    "logs/log_config_cases.json"
)


def build_source(
    required: bool = True,
) -> LogSourceConfig:
    """Build a controlled log source."""
    source_values = CASES["source"]

    return LogSourceConfig(
        source_id=source_values["source_id"],
        label=source_values["label"],
        path=source_values["path"],
        required=required,
    )


def build_config(
    source: LogSourceConfig,
) -> LogAnalyzerConfig:
    """Build complete log analyzer configuration."""
    return LogAnalyzerConfig(
        collection=LogCollectionConfig(
            encoding="utf-8",
            max_lines_per_source=100,
        ),
        sources=(source,),
        rules=(
            LogRuleConfig(
                rule_id="error",
                label="Error event",
                pattern="ERROR",
                severity=HealthStatus.CRITICAL,
                case_sensitive=False,
            ),
        ),
        report=LogReportConfig(
            **CONFIG_CASES["valid_report"]
        ),
    )


def build_match(
    case_name: str,
    severity: HealthStatus,
) -> LogMatch:
    """Build one controlled log match."""
    return LogMatch(
        **CASES[case_name],
        severity=severity,
    )


@dataclass
class FakeLogScanner:
    """Return one controlled log source result."""

    result: LogSourceResult

    def scan(
        self,
        source: LogSourceConfig,
    ) -> LogSourceResult:
        return self.result


class TestLogAnalyzer:
    """Test log source health evaluation."""

    def test_returns_healthy_without_matches(self) -> None:
        source = build_source()
        result = LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=source.required,
            status=LogScanStatus.ANALYZED,
            total_lines_scanned=10,
        )
        analyzer = LogAnalyzer(
            config=build_config(source),
            scanner=FakeLogScanner(result),
        )

        summary = analyzer.run()

        assert summary.overall_status is HealthStatus.HEALTHY

    def test_returns_warning_for_warning_match(self) -> None:
        source = build_source()
        result = LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=source.required,
            status=LogScanStatus.ANALYZED,
            total_lines_scanned=10,
            matches=(
                build_match(
                    "warning_match",
                    HealthStatus.WARNING,
                ),
            ),
        )
        analyzer = LogAnalyzer(
            config=build_config(source),
            scanner=FakeLogScanner(result),
        )

        summary = analyzer.run()

        assert summary.overall_status is HealthStatus.WARNING

    def test_returns_critical_for_critical_match(self) -> None:
        source = build_source()
        result = LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=source.required,
            status=LogScanStatus.ANALYZED,
            total_lines_scanned=10,
            matches=(
                build_match(
                    "critical_match",
                    HealthStatus.CRITICAL,
                ),
            ),
        )
        analyzer = LogAnalyzer(
            config=build_config(source),
            scanner=FakeLogScanner(result),
        )

        summary = analyzer.run()

        assert summary.overall_status is HealthStatus.CRITICAL

    def test_required_scan_error_is_critical(self) -> None:
        source = build_source(required=True)
        result = LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=True,
            status=LogScanStatus.CHECK_ERROR,
            total_lines_scanned=0,
            failure_reason=LogFailureReason.FILE_NOT_FOUND,
            error_message="Log file was not found.",
        )
        analyzer = LogAnalyzer(
            config=build_config(source),
            scanner=FakeLogScanner(result),
        )

        summary = analyzer.run()

        assert summary.overall_status is HealthStatus.CRITICAL

    def test_optional_scan_error_is_warning(self) -> None:
        source = build_source(required=False)
        result = LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=False,
            status=LogScanStatus.CHECK_ERROR,
            total_lines_scanned=0,
            failure_reason=LogFailureReason.FILE_NOT_FOUND,
            error_message="Log file was not found.",
        )
        analyzer = LogAnalyzer(
            config=build_config(source),
            scanner=FakeLogScanner(result),
        )

        summary = analyzer.run()

        assert summary.overall_status is HealthStatus.WARNING

    def test_rejects_invalid_scanner_dependency(self) -> None:
        source = build_source()

        with pytest.raises(
            TypeError,
            match="callable scan method",
        ):
            LogAnalyzer(
                config=build_config(source),
                scanner=object(),
            )