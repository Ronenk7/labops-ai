"""Tests for the read-only incident API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from labops_ai.api import (
    IncidentApiService,
    RunHistoryApiService,
    create_app,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry
from labops_ai.incidents import (
    IncidentRecord,
    IncidentSourceType,
    IncidentStatus,
    IncidentStoreState,
)


pytestmark = pytest.mark.unit
NOW = datetime(
    2026,
    7,
    19,
    20,
    0,
    tzinfo=timezone.utc,
)


@dataclass
class FakeIncidentReader:
    """Return deterministic incident state."""

    state: IncidentStoreState

    def load(self) -> IncidentStoreState:
        return self.state


@dataclass
class FakeHistoryReader:
    """Provide the history methods required by the API."""

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        return None

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        return None

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        return ()


def build_incident(
    incident_id: str,
    *,
    status: IncidentStatus,
    severity: HealthStatus,
    source_type: IncidentSourceType,
    minutes_ago: int,
) -> IncidentRecord:
    """Build one deterministic incident record."""
    last_seen = NOW - timedelta(minutes=minutes_ago)
    resolved_at = (
        last_seen + timedelta(minutes=1)
        if status is IncidentStatus.RESOLVED
        else None
    )

    return IncidentRecord(
        incident_id=incident_id,
        source_type=source_type,
        source_id=incident_id.casefold(),
        source_label=f"Source {incident_id}",
        severity=severity,
        status=status,
        description=f"Description for {incident_id}",
        first_seen_at=last_seen - timedelta(minutes=5),
        last_seen_at=last_seen,
        occurrence_count=2,
        resolved_at=resolved_at,
    )


def build_client() -> TestClient:
    """Build an API client with deterministic services."""
    state = IncidentStoreState(
        next_sequence=4,
        incidents=(
            build_incident(
                "INC-0001",
                status=IncidentStatus.OPEN,
                severity=HealthStatus.CRITICAL,
                source_type=IncidentSourceType.SERVICE,
                minutes_ago=1,
            ),
            build_incident(
                "INC-0002",
                status=IncidentStatus.ACKNOWLEDGED,
                severity=HealthStatus.WARNING,
                source_type=IncidentSourceType.NETWORK,
                minutes_ago=2,
            ),
            build_incident(
                "INC-0003",
                status=IncidentStatus.RESOLVED,
                severity=HealthStatus.WARNING,
                source_type=IncidentSourceType.LOG,
                minutes_ago=3,
            ),
        ),
    )

    return TestClient(
        create_app(
            RunHistoryApiService(
                reader=FakeHistoryReader()
            ),
            IncidentApiService(
                reader=FakeIncidentReader(state)
            ),
        )
    )


def test_lists_incidents_newest_first() -> None:
    response = build_client().get("/api/v1/incidents")

    assert response.status_code == 200
    assert [
        incident["incident_id"]
        for incident in response.json()
    ] == [
        "INC-0001",
        "INC-0002",
        "INC-0003",
    ]


def test_filters_active_critical_incidents() -> None:
    response = build_client().get(
        "/api/v1/incidents",
        params={
            "active_only": "true",
            "severity": "CRITICAL",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["incident_id"] == "INC-0001"


def test_returns_incident_summary() -> None:
    response = build_client().get(
        "/api/v1/incidents/summary"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["active"] == 2
    assert response.json()["resolved"] == 1
    assert response.json()["critical"] == 1


def test_returns_incident_by_id() -> None:
    response = build_client().get(
        "/api/v1/incidents/INC-0002"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"
    assert response.json()["is_active"] is True


def test_returns_404_for_unknown_incident() -> None:
    response = build_client().get(
        "/api/v1/incidents/INC-9999"
    )

    assert response.status_code == 404
