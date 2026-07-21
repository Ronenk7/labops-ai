"""Tests for monitored-host API routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from labops_ai.api.host_routes import (
    build_host_router,
)
from labops_ai.hosts import (
    HostAvailabilityPolicy,
    HostHeartbeat,
    HostRecord,
    HostRegistryError,
    HostRegistryService,
    HostStatusEvaluator,
)


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    20,
    12,
    0,
    tzinfo=timezone.utc,
)


class InMemoryHostRegistry:
    """Provide deterministic host storage for route tests."""

    def __init__(
        self,
        hosts: tuple[HostRecord, ...] = (),
    ) -> None:
        """Initialize the registry."""
        self.hosts = {
            host.host_id: host
            for host in hosts
        }

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Create or update one host."""
        current = self.hosts.get(
            heartbeat.host_id
        )

        record = (
            HostRecord.register(heartbeat)
            if current is None
            else current.apply_heartbeat(heartbeat)
        )

        self.hosts[record.host_id] = record
        return record

    def get_by_id(
        self,
        host_id: str,
    ) -> HostRecord | None:
        """Return one host."""
        return self.hosts.get(host_id.strip())

    def list_all(self) -> tuple[HostRecord, ...]:
        """Return all hosts."""
        return tuple(self.hosts.values())


class FailingHostRegistry(InMemoryHostRegistry):
    """Simulate an unavailable SQLite registry."""

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Raise a deterministic storage failure."""
        raise HostRegistryError(
            "Simulated registry failure."
        )


def build_service(
    registry: InMemoryHostRegistry,
) -> HostRegistryService:
    """Create the production-style host service."""
    return HostRegistryService(
        registry=registry,
        evaluator=HostStatusEvaluator(
            HostAvailabilityPolicy(
                stale_after_seconds=30,
                offline_after_seconds=120,
            )
        ),
        clock=lambda: BASE_TIME,
    )


def build_client(
    registry: InMemoryHostRegistry,
) -> TestClient:
    """Create an isolated API client."""
    application = FastAPI()
    application.include_router(
        build_host_router(
            build_service(registry)
        )
    )

    return TestClient(application)


def build_payload(
    *,
    observed_at: datetime = BASE_TIME,
) -> dict[str, object]:
    """Create one valid heartbeat request body."""
    return {
        "host_id": "host-001",
        "host_name": "lab-node-01",
        "address": "10.0.0.10",
        "operating_system": "Ubuntu 24.04",
        "architecture": "x86_64",
        "agent_version": "0.1.0",
        "observed_at": observed_at.isoformat(),
    }


def test_records_new_host_heartbeat() -> None:
    """Register a host and return its current status."""
    response = build_client(
        InMemoryHostRegistry()
    ).post(
        "/api/v1/hosts/heartbeat",
        json=build_payload(),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["host_id"] == "host-001"
    assert payload["host_name"] == "lab-node-01"
    assert payload["availability"] == "ONLINE"
    assert payload["heartbeat_age_seconds"] == 0
    assert payload["last_seen_at"].startswith(
        "2026-07-20T12:00:00"
    )


def test_updates_existing_host() -> None:
    """Accept a newer heartbeat for an existing host."""
    registry = InMemoryHostRegistry()
    client = build_client(registry)

    first_response = client.post(
        "/api/v1/hosts/heartbeat",
        json=build_payload(),
    )

    later_time = BASE_TIME + timedelta(seconds=10)
    updated_payload = build_payload(
        observed_at=later_time
    )
    updated_payload["host_name"] = "renamed-node"

    second_response = client.post(
        "/api/v1/hosts/heartbeat",
        json=updated_payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert (
        second_response.json()["host_name"]
        == "renamed-node"
    )
    assert (
        second_response.json()["registered_at"]
        == first_response.json()["registered_at"]
    )


def test_rejects_older_heartbeat() -> None:
    """Return HTTP 409 for an outdated heartbeat."""
    latest_time = BASE_TIME + timedelta(minutes=1)

    latest_host = HostRecord.register(
        HostHeartbeat(
            host_id="host-001",
            host_name="lab-node-01",
            address="10.0.0.10",
            operating_system="Ubuntu 24.04",
            architecture="x86_64",
            agent_version="0.1.0",
            observed_at=latest_time,
        )
    )

    response = build_client(
        InMemoryHostRegistry((latest_host,))
    ).post(
        "/api/v1/hosts/heartbeat",
        json=build_payload(
            observed_at=BASE_TIME
        ),
    )

    assert response.status_code == 409
    assert "older than" in response.json()["detail"]


def test_returns_503_when_registry_fails() -> None:
    """Hide storage details behind HTTP 503."""
    response = build_client(
        FailingHostRegistry()
    ).post(
        "/api/v1/hosts/heartbeat",
        json=build_payload(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Host registry is temporarily "
            "unavailable."
        )
    }


def test_rejects_naive_timestamp() -> None:
    """Return HTTP 422 for a timestamp without timezone."""
    payload = build_payload()
    payload["observed_at"] = "2026-07-20T12:00:00"

    response = build_client(
        InMemoryHostRegistry()
    ).post(
        "/api/v1/hosts/heartbeat",
        json=payload,
    )

    assert response.status_code == 422


def test_rejects_unknown_request_field() -> None:
    """Return HTTP 422 for unsupported input."""
    payload = build_payload()
    payload["unexpected"] = True

    response = build_client(
        InMemoryHostRegistry()
    ).post(
        "/api/v1/hosts/heartbeat",
        json=payload,
    )

    assert response.status_code == 422


def test_rejects_invalid_service_dependency() -> None:
    """Require a real HostRegistryService."""
    with pytest.raises(
        TypeError,
        match="HostRegistryService",
    ):
        build_host_router(object())



class FailingReadHostRegistry(InMemoryHostRegistry):
    """Simulate host-registry read failures."""

    def get_by_id(
        self,
        host_id: str,
    ) -> HostRecord | None:
        """Fail while reading one host."""
        raise HostRegistryError(
            "Simulated registry read failure."
        )

    def list_all(self) -> tuple[HostRecord, ...]:
        """Fail while listing hosts."""
        raise HostRegistryError(
            "Simulated registry read failure."
        )


def build_registered_host(
    *,
    host_id: str,
    host_name: str,
    observed_at: datetime,
) -> HostRecord:
    """Create one registered host for read tests."""
    return HostRecord.register(
        HostHeartbeat(
            host_id=host_id,
            host_name=host_name,
            address=f"10.0.0.{host_id[-1]}",
            operating_system="Ubuntu 24.04",
            architecture="x86_64",
            agent_version="0.1.0",
            observed_at=observed_at,
        )
    )


def test_lists_hosts_with_calculated_availability() -> None:
    """Return all hosts with status calculated at read time."""
    online_host = build_registered_host(
        host_id="host-001",
        host_name="online-node",
        observed_at=BASE_TIME,
    )
    offline_host = build_registered_host(
        host_id="host-002",
        host_name="offline-node",
        observed_at=(
            BASE_TIME - timedelta(seconds=120)
        ),
    )

    response = build_client(
        InMemoryHostRegistry(
            (online_host, offline_host)
        )
    ).get("/api/v1/hosts")

    assert response.status_code == 200

    hosts = {
        item["host_id"]: item
        for item in response.json()
    }

    assert hosts["host-001"]["availability"] == "ONLINE"
    assert hosts["host-002"]["availability"] == "OFFLINE"
    assert (
        hosts["host-002"]["heartbeat_age_seconds"]
        == 120
    )


def test_gets_host_by_id() -> None:
    """Return one registered host."""
    host = build_registered_host(
        host_id="host-001",
        host_name="lab-node-01",
        observed_at=BASE_TIME,
    )

    response = build_client(
        InMemoryHostRegistry((host,))
    ).get("/api/v1/hosts/host-001")

    assert response.status_code == 200
    assert response.json()["host_id"] == "host-001"
    assert response.json()["availability"] == "ONLINE"


def test_returns_404_for_unknown_host() -> None:
    """Return HTTP 404 when the host does not exist."""
    response = build_client(
        InMemoryHostRegistry()
    ).get("/api/v1/hosts/missing-host")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Host missing-host was not found."
    }


def test_returns_503_when_host_list_fails() -> None:
    """Convert host-list storage failures to HTTP 503."""
    response = build_client(
        FailingReadHostRegistry()
    ).get("/api/v1/hosts")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Host registry is temporarily "
            "unavailable."
        )
    }


def test_returns_503_when_host_read_fails() -> None:
    """Convert single-host storage failures to HTTP 503."""
    response = build_client(
        FailingReadHostRegistry()
    ).get("/api/v1/hosts/host-001")

    assert response.status_code == 503
