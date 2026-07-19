"""Unit tests for incident management reports."""
from __future__ import annotations

from datetime import datetime

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentActionResult,
    IncidentActionType,
    IncidentManagementConfigLoader,
    IncidentRecord,
    IncidentSignal,
    IncidentSourceType,
    IncidentStatus,
    IncidentStoreState,
    build_incident_report,
    print_incident_report,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
REPORT_CASES = load_test_fixture(
    "incidents/incident_report_cases.json"
)
STORE_CASES = load_test_fixture(
    "incidents/incident_store_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse one ISO 8601 fixture datetime."""
    return datetime.fromisoformat(value)


def build_incident(case_name: str) -> IncidentRecord:
    """Build one incident from external fixture data."""
    case = STORE_CASES[case_name]

    return IncidentRecord(
        incident_id=case["incident_id"],
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        status=IncidentStatus(case["status"]),
        description=case["description"],
        first_seen_at=parse_datetime(case["first_seen_at"]),
        last_seen_at=parse_datetime(case["last_seen_at"]),
        occurrence_count=case["occurrence_count"],
        resolved_at=(
            parse_datetime(case["resolved_at"])
            if case["resolved_at"] is not None
            else None
        ),
    )


def build_signal(case_name: str) -> IncidentSignal:
    """Build one incident signal from external fixture data."""
    case = REPORT_CASES[case_name]

    return IncidentSignal(
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        description=case["description"],
        observed_at=parse_datetime(case["observed_at"]),
    )


def build_report_config():
    """Load the project incident report configuration."""
    return IncidentManagementConfigLoader().load().report


class TestBuildIncidentReport:
    """Test incident report construction."""

    def test_builds_empty_incident_report(self) -> None:
        state = IncidentStoreState(
            next_sequence=1,
            incidents=(),
        )

        result = build_incident_report(
            actions=(),
            state=state,
            report=build_report_config(),
        )

        assert result.splitlines() == (
            REPORT_CASES["empty_report_lines"]
        )

    def test_builds_populated_incident_report(self) -> None:
        active = build_incident("active_incident")
        resolved = build_incident("resolved_incident")
        state = IncidentStoreState(
            next_sequence=3,
            incidents=(active, resolved),
        )
        actions = (
            IncidentActionResult(
                action_type=IncidentActionType.CREATED,
                signal=build_signal("created_signal"),
                incident=active,
            ),
            IncidentActionResult(
                action_type=IncidentActionType.RESOLVED,
                signal=build_signal("resolved_signal"),
                incident=resolved,
            ),
        )

        result = build_incident_report(
            actions=actions,
            state=state,
            report=build_report_config(),
        )

        assert result.splitlines() == (
            REPORT_CASES["populated_report_lines"]
        )

    def test_rejects_non_tuple_actions(self) -> None:
        with pytest.raises(
            TypeError,
            match="actions must be a tuple",
        ):
            build_incident_report(
                actions=[],
                state=IncidentStoreState(
                    next_sequence=1,
                    incidents=(),
                ),
                report=build_report_config(),
            )

    def test_rejects_invalid_action_item(self) -> None:
        with pytest.raises(
            TypeError,
            match="Every action",
        ):
            build_incident_report(
                actions=(object(),),
                state=IncidentStoreState(
                    next_sequence=1,
                    incidents=(),
                ),
                report=build_report_config(),
            )

    def test_rejects_invalid_state(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncidentStoreState",
        ):
            build_incident_report(
                actions=(),
                state=object(),
                report=build_report_config(),
            )

    def test_rejects_invalid_report_configuration(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncidentReportConfig",
        ):
            build_incident_report(
                actions=(),
                state=IncidentStoreState(
                    next_sequence=1,
                    incidents=(),
                ),
                report=object(),
            )


class TestPrintIncidentReport:
    """Test printing the incident management report."""

    def test_prints_incident_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        state = IncidentStoreState(
            next_sequence=1,
            incidents=(),
        )

        print_incident_report(
            actions=(),
            state=state,
            report=build_report_config(),
        )

        captured = capsys.readouterr()

        assert captured.out.strip().splitlines() == (
            REPORT_CASES["empty_report_lines"]
        )