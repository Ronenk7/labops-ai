"""Unit tests for incident management domain models."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentActionResult,
    IncidentActionType,
    IncidentRecord,
    IncidentSignal,
    IncidentSourceType,
    IncidentStatus,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_models_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse one ISO 8601 fixture timestamp."""
    return datetime.fromisoformat(value)


def build_signal(
    case_name: str = "signal",
) -> IncidentSignal:
    """Build one incident signal from external test data."""
    case = CASES[case_name]

    return IncidentSignal(
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        description=case["description"],
        observed_at=parse_datetime(case["observed_at"]),
    )


def build_incident(
    case_name: str = "active_incident",
) -> IncidentRecord:
    """Build one incident record from external test data."""
    case = CASES[case_name]

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
            if case.get("resolved_at")
            else None
        ),
    )


class TestIncidentSignal:
    """Test health observations supplied to incident management."""

    def test_accepts_and_normalizes_signal(self) -> None:
        signal = build_signal()

        assert signal.source_type is IncidentSourceType.SERVICE
        assert signal.severity is HealthStatus.CRITICAL
        assert signal.observed_at.tzinfo is timezone.utc
        assert signal.incident_key == (
            "SERVICE:systemd-journald.service"
        )

    def test_accepts_healthy_recovery_signal(self) -> None:
        signal = build_signal("healthy_signal")

        assert signal.severity is HealthStatus.HEALTHY

    def test_rejects_datetime_without_timezone(self) -> None:
        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            IncidentSignal(
                source_type=IncidentSourceType.SYSTEM,
                source_id="cpu",
                source_label="CPU",
                severity=HealthStatus.WARNING,
                description="CPU usage is high.",
                observed_at=datetime(2026, 7, 19, 9, 0),
            )


class TestIncidentRecord:
    """Test persisted incident lifecycle records."""

    def test_accepts_active_incident(self) -> None:
        incident = build_incident()

        assert incident.status is IncidentStatus.OPEN
        assert incident.is_active is True
        assert incident.resolved_at is None
        assert incident.occurrence_count == 2

    def test_accepts_resolved_incident(self) -> None:
        incident = build_incident("resolved_incident")

        assert incident.status is IncidentStatus.RESOLVED
        assert incident.is_active is False
        assert incident.resolved_at is not None

    def test_rejects_healthy_incident_severity(self) -> None:
        case = CASES["active_incident"]

        with pytest.raises(
            ValueError,
            match="WARNING or CRITICAL",
        ):
            IncidentRecord(
                incident_id=case["incident_id"],
                source_type=IncidentSourceType.SERVICE,
                source_id=case["source_id"],
                source_label=case["source_label"],
                severity=HealthStatus.HEALTHY,
                status=IncidentStatus.OPEN,
                description=case["description"],
                first_seen_at=parse_datetime(
                    case["first_seen_at"]
                ),
                last_seen_at=parse_datetime(
                    case["last_seen_at"]
                ),
                occurrence_count=1,
            )

    def test_rejects_last_seen_before_first_seen(self) -> None:
        with pytest.raises(
            ValueError,
            match="last seen time",
        ):
            IncidentRecord(
                incident_id="INC-000001",
                source_type=IncidentSourceType.SYSTEM,
                source_id="cpu",
                source_label="CPU",
                severity=HealthStatus.WARNING,
                status=IncidentStatus.OPEN,
                description="CPU usage is high.",
                first_seen_at=parse_datetime(
                    "2026-07-19T10:00:00+00:00"
                ),
                last_seen_at=parse_datetime(
                    "2026-07-19T09:00:00+00:00"
                ),
                occurrence_count=1,
            )

    def test_rejects_active_incident_with_resolution_time(
        self,
    ) -> None:
        case = CASES["active_incident"]

        with pytest.raises(
            ValueError,
            match="active incident",
        ):
            IncidentRecord(
                incident_id=case["incident_id"],
                source_type=IncidentSourceType.SERVICE,
                source_id=case["source_id"],
                source_label=case["source_label"],
                severity=HealthStatus.CRITICAL,
                status=IncidentStatus.OPEN,
                description=case["description"],
                first_seen_at=parse_datetime(
                    case["first_seen_at"]
                ),
                last_seen_at=parse_datetime(
                    case["last_seen_at"]
                ),
                occurrence_count=1,
                resolved_at=parse_datetime(
                    "2026-07-19T09:05:00+03:00"
                ),
            )

    def test_rejects_resolved_incident_without_resolution_time(
        self,
    ) -> None:
        case = CASES["active_incident"]

        with pytest.raises(
            ValueError,
            match="resolution time",
        ):
            IncidentRecord(
                incident_id=case["incident_id"],
                source_type=IncidentSourceType.SERVICE,
                source_id=case["source_id"],
                source_label=case["source_label"],
                severity=HealthStatus.CRITICAL,
                status=IncidentStatus.RESOLVED,
                description=case["description"],
                first_seen_at=parse_datetime(
                    case["first_seen_at"]
                ),
                last_seen_at=parse_datetime(
                    case["last_seen_at"]
                ),
                occurrence_count=1,
            )


class TestIncidentActionResult:
    """Test results produced while processing signals."""

    def test_accepts_created_action(self) -> None:
        action = IncidentActionResult(
            action_type=IncidentActionType.CREATED,
            signal=build_signal(),
            incident=build_incident(),
        )

        assert action.incident is not None
        assert action.incident.is_active is True

    def test_accepts_resolved_action(self) -> None:
        action = IncidentActionResult(
            action_type=IncidentActionType.RESOLVED,
            signal=build_signal("healthy_signal"),
            incident=build_incident("resolved_incident"),
        )

        assert action.incident is not None
        assert action.incident.status is IncidentStatus.RESOLVED

    def test_accepts_unchanged_action_without_incident(self) -> None:
        action = IncidentActionResult(
            action_type=IncidentActionType.UNCHANGED,
            signal=build_signal("healthy_signal"),
        )

        assert action.incident is None

    def test_rejects_changed_action_without_incident(self) -> None:
        with pytest.raises(
            ValueError,
            match="must contain an incident",
        ):
            IncidentActionResult(
                action_type=IncidentActionType.CREATED,
                signal=build_signal(),
            )