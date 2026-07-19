"""Unit tests for text file log scanning."""
from __future__ import annotations

from pathlib import Path

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.logs import (
    FileLogScanner,
    LogAnalyzerConfig,
    LogCollectionConfig,
    LogFailureReason,
    LogLine,
    LogReportConfig,
    LogRuleConfig,
    LogScanStatus,
    LogSourceConfig,
    read_log_tail,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "logs/file_log_scanner_cases.json"
)
CONFIG_CASES = load_test_fixture(
    "logs/log_config_cases.json"
)


def build_source() -> LogSourceConfig:
    """Build the configured log source."""
    return LogSourceConfig(**CASES["source"])


def build_config() -> LogAnalyzerConfig:
    """Build complete scanner configuration."""
    rules = (
        LogRuleConfig(
            rule_id="timeout",
            label="Timeout event",
            pattern=r"\bTIMEOUT\b",
            severity=HealthStatus.WARNING,
            case_sensitive=False,
        ),
        LogRuleConfig(
            rule_id="error",
            label="Error event",
            pattern=r"\bERROR\b",
            severity=HealthStatus.CRITICAL,
            case_sensitive=False,
        ),
        LogRuleConfig(
            rule_id="connection-refused",
            label="Connection refused",
            pattern="connection refused",
            severity=HealthStatus.CRITICAL,
            case_sensitive=False,
        ),
    )

    return LogAnalyzerConfig(
        collection=LogCollectionConfig(
            encoding="utf-8",
            max_lines_per_source=500,
        ),
        sources=(build_source(),),
        rules=rules,
        report=LogReportConfig(
            **CONFIG_CASES["valid_report"]
        ),
    )


def build_lines() -> tuple[LogLine, ...]:
    """Build controlled log lines from external data."""
    return tuple(
        LogLine(**line)
        for line in CASES["lines"]
    )


class TestReadLogTail:
    """Test efficient final-line collection."""

    def test_returns_only_final_configured_lines(
        self,
        tmp_path: Path,
    ) -> None:
        log_path = tmp_path / "application.log"
        log_path.write_text(
            "\n".join(CASES["tail_file_lines"]) + "\n",
            encoding="utf-8",
        )

        lines = read_log_tail(
            path=log_path,
            encoding="utf-8",
            max_lines=2,
        )

        assert [
            line.line_number
            for line in lines
        ] == CASES["expected_tail_line_numbers"]
        assert [
            line.text
            for line in lines
        ] == CASES["tail_file_lines"][-2:]


class TestFileLogScanner:
    """Test rule matching and normalized failures."""

    def test_returns_all_matching_rules(self) -> None:
        scanner = FileLogScanner(
            config=build_config(),
            reader=lambda path, encoding, maximum: build_lines(),
        )

        result = scanner.scan(build_source())

        assert result.status is LogScanStatus.ANALYZED
        assert result.total_lines_scanned == 4
        assert [
            match.rule_id
            for match in result.matches
        ] == CASES["expected_rule_ids"]

    def test_returns_analyzed_result_without_matches(
        self,
    ) -> None:
        lines = (
            LogLine(
                line_number=1,
                text="INFO Application started",
            ),
        )
        scanner = FileLogScanner(
            config=build_config(),
            reader=lambda path, encoding, maximum: lines,
        )

        result = scanner.scan(build_source())

        assert result.status is LogScanStatus.ANALYZED
        assert result.matches == ()

    def test_returns_file_not_found_error(self) -> None:
        def missing_reader(
            path: Path,
            encoding: str,
            maximum: int,
        ) -> tuple[LogLine, ...]:
            raise FileNotFoundError("Log file is missing.")

        scanner = FileLogScanner(
            config=build_config(),
            reader=missing_reader,
        )

        result = scanner.scan(build_source())

        assert result.status is LogScanStatus.CHECK_ERROR
        assert (
            result.failure_reason
            is LogFailureReason.FILE_NOT_FOUND
        )

    def test_returns_access_denied_error(self) -> None:
        def denied_reader(
            path: Path,
            encoding: str,
            maximum: int,
        ) -> tuple[LogLine, ...]:
            raise PermissionError("Permission denied.")

        scanner = FileLogScanner(
            config=build_config(),
            reader=denied_reader,
        )

        result = scanner.scan(build_source())

        assert (
            result.failure_reason
            is LogFailureReason.ACCESS_DENIED
        )

    def test_returns_decode_error(self) -> None:
        def invalid_encoding_reader(
            path: Path,
            encoding: str,
            maximum: int,
        ) -> tuple[LogLine, ...]:
            raise UnicodeDecodeError(
                "utf-8",
                b"\xff",
                0,
                1,
                "invalid start byte",
            )

        scanner = FileLogScanner(
            config=build_config(),
            reader=invalid_encoding_reader,
        )

        result = scanner.scan(build_source())

        assert (
            result.failure_reason
            is LogFailureReason.DECODE_ERROR
        )

    def test_returns_read_error(self) -> None:
        def failed_reader(
            path: Path,
            encoding: str,
            maximum: int,
        ) -> tuple[LogLine, ...]:
            raise OSError("Storage device unavailable.")

        scanner = FileLogScanner(
            config=build_config(),
            reader=failed_reader,
        )

        result = scanner.scan(build_source())

        assert (
            result.failure_reason
            is LogFailureReason.READ_ERROR
        )

    def test_rejects_invalid_source(self) -> None:
        scanner = FileLogScanner(config=build_config())

        with pytest.raises(
            TypeError,
            match="LogSourceConfig",
        ):
            scanner.scan(object())