"""Unit tests for diagnostic JSON and text reports."""
from __future__ import annotations

import json

import pytest

from labops_ai.diagnostics.diagnostic_report import (
    build_diagnostic_json,
    build_diagnostic_payload,
    build_diagnostic_text,
)
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_report_cases.json"
)


class TestBuildDiagnosticPayload:
    """Test structured diagnostic report payloads."""

    def test_builds_complete_payload(self) -> None:
        snapshot = build_test_diagnostic_snapshot()

        payload = build_diagnostic_payload(snapshot)

        assert payload["schema_version"] == (
            CASES["schema_version"]
        )
        assert payload["generated_at"] == (
            CASES["generated_at"]
        )
        assert payload["host_name"] == CASES["host_name"]
        assert payload["overall_status"] == (
            CASES["overall_status"]
        )
        assert payload["summary"]["active_incidents"] == (
            CASES["active_incidents"]
        )
        assert payload["summary"]["resolved_incidents"] == (
            CASES["resolved_incidents"]
        )

    def test_preserves_failure_and_metric_details(
        self,
    ) -> None:
        payload = build_diagnostic_payload(
            build_test_diagnostic_snapshot()
        )

        tcp_check = payload["network"]["checks"][1]
        process = payload["processes"]["records"][0]
        log = payload["logs"]["records"][0]

        assert tcp_check["failure_reason"] == "TIMEOUT"
        assert tcp_check["error_message"] == (
            "Connection timed out."
        )
        assert process["pids"] == [100]
        assert process["total_memory_mb"] == 450.25
        assert log["failure_reason"] == "FILE_NOT_FOUND"

    def test_rejects_invalid_snapshot(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            build_diagnostic_payload(object())


class TestBuildDiagnosticJson:
    """Test JSON diagnostic report rendering."""

    def test_builds_valid_json_report(self) -> None:
        report = build_diagnostic_json(
            build_test_diagnostic_snapshot()
        )

        payload = json.loads(report)

        assert payload["overall_status"] == "CRITICAL"
        assert len(payload["system"]["metrics"]) == 2
        assert len(payload["network"]["checks"]) == 2
        assert len(payload["incidents"]["records"]) == 2
        assert report.endswith("\n")

    def test_returns_deterministic_json(self) -> None:
        snapshot = build_test_diagnostic_snapshot()

        first_report = build_diagnostic_json(snapshot)
        second_report = build_diagnostic_json(snapshot)

        assert first_report == second_report

    def test_rejects_invalid_snapshot(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            build_diagnostic_json(object())


class TestBuildDiagnosticText:
    """Test human-readable diagnostic reports."""

    def test_contains_every_diagnostic_section(self) -> None:
        report = build_diagnostic_text(
            build_test_diagnostic_snapshot()
        )

        assert report.startswith(
            "LabOps AI Diagnostic Report\n"
        )

        for section_header in CASES["section_headers"]:
            assert section_header in report

    def test_contains_metrics_and_failure_details(
        self,
    ) -> None:
        report = build_diagnostic_text(
            build_test_diagnostic_snapshot()
        )

        for expected_line in CASES["expected_text_lines"]:
            assert expected_line in report

    def test_contains_incident_summary_and_records(
        self,
    ) -> None:
        report = build_diagnostic_text(
            build_test_diagnostic_snapshot()
        )

        assert "Active incidents: 1" in report
        assert "Resolved incidents: 1" in report
        assert "Status: OPEN" in report
        assert "Status: RESOLVED" in report
        assert report.endswith("\n")

    def test_rejects_invalid_snapshot(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            build_diagnostic_text(object())