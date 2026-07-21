"""Tests for Host drill-down API aggregation."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from labops_ai.api.host_drilldown import (
    build_host_drilldown_router,
)
from labops_ai.api.schemas import RunHistoryResponse
from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryQueryError
from labops_ai.hosts import (
    HostAvailability,
    HostHeartbeat,
    HostRecord,
    HostRegistryError,
    HostStatusSnapshot,
)


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    21,
    12,
    0,
    tzinfo=timezone.utc,
)


class StaticHostReader:
    """Return one deterministic Host snapshot."""

    def __init__(
        self,
        snapshot: HostStatusSnapshot | None,
        error: Exception | None = None,
    ) -> None:
        """Initialize the fake reader."""
        self.snapshot = snapshot
        self.error = error
        self.requested_host_ids: list[str] = []

    def get_by_id(
        self,
        host_id: str,
    ) -> HostStatusSnapshot | None:
        """Return or fail for one Host identifier."""
        self.requested_host_ids.append(host_id)

        if self.error is not None:
            raise self.error

        return self.snapshot


class StaticRunReader:
    """Return deterministic monitoring-run responses."""

    def __init__(
        self,
        runs: tuple[RunHistoryResponse, ...] = (),
        error: Exception | None = None,
    ) -> None:
        """Initialize the fake reader."""
        self.runs = runs
        self.error = error
        self.calls: list[
            tuple[
                int,
                HealthStatus | None,
                str | None,
            ]
        ] = []

    def list_recent(
        self,
        *,
        limit: int,
        status: HealthStatus | None,
        host_name: str | None,
    ) -> list[RunHistoryResponse]:
        """Return limited runs or raise an error."""
        self.calls.append(
            (
                limit,
                status,
                host_name,
            )
        )

        if self.error is not None:
            raise self.error

        return list(self.runs[:limit])


def build_snapshot() -> HostStatusSnapshot:
    """Create one ONLINE Host snapshot."""
    host = HostRecord.register(
        HostHeartbeat(
            host_id="host-001",
            host_name="lab-node-01",
            address="10.0.0.10",
            operating_system="Ubuntu 24.04",
            architecture="x86_64",
            agent_version="0.5.0",
            observed_at=BASE_TIME,
        )
    )

    return HostStatusSnapshot(
        host=host,
        availability=HostAvailability.ONLINE,
        evaluated_at=BASE_TIME,
        heartbeat_age_seconds=0,
    )


def build_run(
    run_id: int,
    *,
    status: HealthStatus = HealthStatus.HEALTHY,
) -> RunHistoryResponse:
    """Create one API monitoring-run response."""
    return RunHistoryResponse(
        run_id=run_id,
        generated_at=BASE_TIME,
        host_name="lab-node-01",
        overall_status=status,
        system_status=status,
        network_status=status,
        service_status=status,
        process_status=status,
        log_status=status,
        active_incident_count=0,
        resolved_incident_count=0,
        incident_count=0,
        bundle_id=f"bundle-{run_id}",
        archive_path=f"/tmp/run-{run_id}.zip",
    )


def build_client(
    host_reader: StaticHostReader,
    run_reader: StaticRunReader,
) -> TestClient:
    """Create an isolated Host drill-down API."""
    application = FastAPI()
    application.include_router(
        build_host_drilldown_router(
            host_reader=host_reader,
            run_reader=run_reader,
        )
    )

    return TestClient(application)


def test_returns_host_with_recent_runs() -> None:
    """Aggregate Host identity and filtered run history."""
    host_reader = StaticHostReader(build_snapshot())
    run_reader = StaticRunReader(
        (
            build_run(12),
            build_run(
                11,
                status=HealthStatus.WARNING,
            ),
        )
    )

    response = build_client(
        host_reader,
        run_reader,
    ).get(
        "/api/v1/hosts/host-001/overview",
        params={"limit": 1},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["host"]["host_id"] == "host-001"
    assert payload["host"]["availability"] == "ONLINE"
    assert payload["latest_run"]["run_id"] == 12
    assert payload["returned_run_count"] == 1
    assert [run["run_id"] for run in payload["runs"]] == [
        12
    ]
    assert run_reader.calls == [
        (
            1,
            None,
            "lab-node-01",
        )
    ]


def test_returns_host_without_runs() -> None:
    """Represent a registered Host with no monitoring history."""
    response = build_client(
        StaticHostReader(build_snapshot()),
        StaticRunReader(),
    ).get(
        "/api/v1/hosts/host-001/overview"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["latest_run"] is None
    assert payload["returned_run_count"] == 0
    assert payload["runs"] == []


def test_returns_404_for_unknown_host() -> None:
    """Do not query history when the Host does not exist."""
    run_reader = StaticRunReader()

    response = build_client(
        StaticHostReader(None),
        run_reader,
    ).get(
        "/api/v1/hosts/missing-host/overview"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Host missing-host was not found."
    )
    assert run_reader.calls == []


def test_validates_run_limit() -> None:
    """Reject an invalid history limit through FastAPI."""
    response = build_client(
        StaticHostReader(build_snapshot()),
        StaticRunReader(),
    ).get(
        "/api/v1/hosts/host-001/overview",
        params={"limit": 0},
    )

    assert response.status_code == 422


def test_returns_503_when_registry_is_unavailable() -> None:
    """Convert Host Registry storage failures."""
    response = build_client(
        StaticHostReader(
            None,
            error=HostRegistryError(
                "Registry unavailable."
            ),
        ),
        StaticRunReader(),
    ).get(
        "/api/v1/hosts/host-001/overview"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Host drill-down data is temporarily unavailable."
    )


def test_returns_503_when_history_is_unavailable() -> None:
    """Convert run-history storage failures."""
    response = build_client(
        StaticHostReader(build_snapshot()),
        StaticRunReader(
            error=RunHistoryQueryError(
                "History unavailable."
            )
        ),
    ).get(
        "/api/v1/hosts/host-001/overview"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Host drill-down data is temporarily unavailable."
    )
