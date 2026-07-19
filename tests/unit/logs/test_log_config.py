"""Unit tests for log analyzer configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.logs import (
    LogAnalyzerConfig,
    LogCollectionConfig,
    LogReportConfig,
    LogRuleConfig,
    LogSourceConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "logs/log_config_cases.json"
)


def build_collection() -> LogCollectionConfig:
    """Build valid log collection configuration."""
    return LogCollectionConfig(
        **CASES["valid_collection"]
    )


def build_source() -> LogSourceConfig:
    """Build a valid log source."""
    return LogSourceConfig(
        **CASES["valid_source"]
    )


def build_rule() -> LogRuleConfig:
    """Build a valid log matching rule."""
    return LogRuleConfig(
        **CASES["valid_rule"],
        severity=HealthStatus.WARNING,
    )


def build_report() -> LogReportConfig:
    """Build valid log report configuration."""
    return LogReportConfig(
        **CASES["valid_report"]
    )


class TestLogCollectionConfig:
    """Test log collection configuration."""

    def test_accepts_valid_collection_settings(self) -> None:
        config = build_collection()

        assert config.encoding == "utf-8"
        assert config.max_lines_per_source == 500

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_max_lines"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_maximum_lines(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            LogCollectionConfig(
                encoding="utf-8",
                max_lines_per_source=case["value"],
            )


class TestLogSourceConfig:
    """Test individual log source configuration."""

    def test_accepts_valid_source(self) -> None:
        source = build_source()

        assert source.source_id == "application"
        assert source.required is True

    def test_strips_surrounding_whitespace(self) -> None:
        source = LogSourceConfig(
            **CASES["normalized_source"]
        )

        assert source.source_id == "application"
        assert source.label == "Application Log"
        assert source.path == "logs/application.log"

    def test_rejects_non_boolean_required(self) -> None:
        with pytest.raises(TypeError, match="boolean"):
            LogSourceConfig(
                source_id="application",
                label="Application Log",
                path="logs/application.log",
                required=1,
            )


class TestLogRuleConfig:
    """Test individual log matching rules."""

    def test_accepts_valid_rule(self) -> None:
        rule = build_rule()

        assert rule.rule_id == "timeout"
        assert rule.severity is HealthStatus.WARNING

    def test_rejects_healthy_rule_severity(self) -> None:
        with pytest.raises(
            ValueError,
            match="WARNING or CRITICAL",
        ):
            LogRuleConfig(
                **CASES["valid_rule"],
                severity=HealthStatus.HEALTHY,
            )

    def test_rejects_invalid_regular_expression(self) -> None:
        with pytest.raises(
            ValueError,
            match="pattern is invalid",
        ):
            LogRuleConfig(
                rule_id="invalid",
                label="Invalid rule",
                pattern="[",
                severity=HealthStatus.WARNING,
                case_sensitive=False,
            )

    def test_rejects_non_boolean_case_setting(self) -> None:
        with pytest.raises(TypeError, match="boolean"):
            LogRuleConfig(
                rule_id="error",
                label="Error event",
                pattern="ERROR",
                severity=HealthStatus.CRITICAL,
                case_sensitive=0,
            )


class TestLogAnalyzerConfig:
    """Test complete log analyzer configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = LogAnalyzerConfig(
            collection=build_collection(),
            sources=(build_source(),),
            rules=(build_rule(),),
            report=build_report(),
        )

        assert len(config.sources) == 1
        assert len(config.rules) == 1

    def test_rejects_empty_sources(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one log source",
        ):
            LogAnalyzerConfig(
                collection=build_collection(),
                sources=(),
                rules=(build_rule(),),
                report=build_report(),
            )

    def test_rejects_empty_rules(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one log rule",
        ):
            LogAnalyzerConfig(
                collection=build_collection(),
                sources=(build_source(),),
                rules=(),
                report=build_report(),
            )

    def test_rejects_duplicate_source_ids(self) -> None:
        source = build_source()

        with pytest.raises(
            ValueError,
            match="source IDs must be unique",
        ):
            LogAnalyzerConfig(
                collection=build_collection(),
                sources=(source, source),
                rules=(build_rule(),),
                report=build_report(),
            )

    def test_rejects_duplicate_rule_ids(self) -> None:
        rule = build_rule()

        with pytest.raises(
            ValueError,
            match="rule IDs must be unique",
        ):
            LogAnalyzerConfig(
                collection=build_collection(),
                sources=(build_source(),),
                rules=(rule, rule),
                report=build_report(),
            )