"""Unit tests for the read-only LabOps AI API."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from labops_ai.api import (
    RunHistoryApiService,
    create_app,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryEntry,
    RunHistoryQueryError,
)


pytestmark = pytest.mark.unit
NOW = datetime(
    2026,
    7,
    19,
    18,
    30,
    tzinfo=timezone.utc,
)


def build_entry(
    run_id: int,
    *,
    status: HealthStatus = HealthStatus.HEALTHY,
    host_name: str = "Kukner7",
) -> RunHistoryEntry:
    """Build one deterministic API history entry."""
    return RunHistoryEntry(
        run_id=run_id,
        generated_at=NOW,
        host_name=host_name,
        overall_status=status,
        system_status=status,
        network_status=status,
        service_status=status,
        process_status=status,
        log_status=status,
        active_incident_count=1,
        resolved_incident_count=2,
        bundle_id=f"bundle-{run_id}",
        archive_path=f"/tmp/bundle-{run_id}.zip",
    )


@dataclass
class FakeHistoryReader:
    """Provide deterministic history reads for API tests."""

    entries: tuple[RunHistoryEntry, ...]
    fail: bool = False
    calls: list[tuple[object, ...]] = field(
        default_factory=list
    )

    def _raise_when_configured(self) -> None:
        if self.fail:
            raise RunHistoryQueryError(
                "Simulated history failure."
            )

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        self._raise_when_configured()
        self.calls.append(("get_by_id", run_id))

        return next(
            (
                entry
                for entry in self.entries
                if entry.run_id == run_id
            ),
            None,
        )

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        self._raise_when_configured()
        self.calls.append(
            ("get_latest", host_name)
        )

        return next(
            (
                entry
                for entry in self.entries
                if (
                    host_name is None
                    or entry.host_name == host_name
                )
            ),
            None,
        )

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        self._raise_when_configured()
        self.calls.append(
            (
                "list_recent",
                limit,
                status,
                host_name,
            )
        )

        matches = tuple(
            entry
            for entry in self.entries
            if (
                status is None
                or entry.overall_status is status
            )
            and (
                host_name is None
                or entry.host_name == host_name
            )
        )

        return matches[:limit]


def build_client(
    reader: FakeHistoryReader,
) -> TestClient:
    """Build a TestClient with an injected reader."""
    service = RunHistoryApiService(reader=reader)
    return TestClient(create_app(service))


def build_reader(
    *,
    fail: bool = False,
) -> FakeHistoryReader:
    """Build a reader containing multiple runs."""
    return FakeHistoryReader(
        entries=(
            build_entry(3),
            build_entry(
                2,
                status=HealthStatus.WARNING,
            ),
            build_entry(
                1,
                host_name="OtherHost",
            ),
        ),
        fail=fail,
    )


def test_health_endpoint() -> None:
    response = build_client(
        build_reader()
    ).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "LabOps AI API",
        "status": "HEALTHY",
        "version": "0.1.0",
    }


def test_openapi_document_is_available() -> None:
    response = build_client(
        build_reader()
    ).get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == (
        "LabOps AI API"
    )


def test_lists_recent_runs_with_filters() -> None:
    reader = build_reader()
    response = build_client(reader).get(
        "/api/v1/runs",
        params={
            "limit": 1,
            "status": "WARNING",
            "host_name": "Kukner7",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["run_id"] == 2
    assert response.json()[0]["incident_count"] == 3
    assert reader.calls[-1] == (
        "list_recent",
        1,
        HealthStatus.WARNING,
        "Kukner7",
    )


def test_returns_latest_run() -> None:
    response = build_client(
        build_reader()
    ).get("/api/v1/runs/latest")

    assert response.status_code == 200
    assert response.json()["run_id"] == 3


def test_latest_run_returns_not_found() -> None:
    reader = FakeHistoryReader(entries=())

    response = build_client(reader).get(
        "/api/v1/runs/latest"
    )

    assert response.status_code == 404


def test_returns_run_by_identifier() -> None:
    response = build_client(
        build_reader()
    ).get("/api/v1/runs/2")

    assert response.status_code == 200
    assert response.json()["run_id"] == 2


def test_missing_identifier_returns_not_found() -> None:
    response = build_client(
        build_reader()
    ).get("/api/v1/runs/999")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/runs?limit=0",
        "/api/v1/runs?limit=101",
        "/api/v1/runs?status=UNKNOWN",
        "/api/v1/runs/0",
    ],
)
def test_rejects_invalid_request_values(
    url: str,
) -> None:
    response = build_client(
        build_reader()
    ).get(url)

    assert response.status_code == 422


def test_maps_history_failure_to_service_unavailable(
) -> None:
    response = build_client(
        build_reader(fail=True)
    ).get("/api/v1/runs")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Run history is temporarily unavailable."
    )
