"""Tests for the host-registry application service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from labops_ai.hosts import (
    HostAvailability,
    HostAvailabilityPolicy,
    HostHeartbeat,
    HostRecord,
    HostStatusEvaluator,
)
from labops_ai.hosts.service import (
    HostRegistryService,
)


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    20,
    10,
    0,
    tzinfo=timezone.utc,
)


class FakeHostRegistry:
    """Provide deterministic in-memory host storage."""

    def __init__(
        self,
        hosts: tuple[HostRecord, ...] = (),
    ) -> None:
        """Initialize fake storage."""
        self.hosts = {
            host.host_id: host
            for host in hosts
        }

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Create or update a host."""
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


def build_heartbeat(
    *,
    host_id: str = "host-001",
    observed_at: datetime = BASE_TIME,
) -> HostHeartbeat:
    """Create one deterministic heartbeat."""
    return HostHeartbeat(
        host_id=host_id,
        host_name="lab-node-01",
        address="10.0.0.10",
        operating_system="Ubuntu 24.04",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=observed_at,
    )


def build_service(
    registry: FakeHostRegistry,
    *,
    current_time: datetime = BASE_TIME,
) -> HostRegistryService:
    """Create a service with deterministic time."""
    evaluator = HostStatusEvaluator(
        HostAvailabilityPolicy(
            stale_after_seconds=30,
            offline_after_seconds=120,
        )
    )

    return HostRegistryService(
        registry=registry,
        evaluator=evaluator,
        clock=lambda: current_time,
    )


def test_records_new_host_as_online() -> None:
    """Store the first heartbeat and return ONLINE."""
    registry = FakeHostRegistry()
    service = build_service(registry)

    result = service.record_heartbeat(
        build_heartbeat()
    )

    assert result.host.host_id == "host-001"
    assert result.availability is HostAvailability.ONLINE
    assert result.heartbeat_age_seconds == 0
    assert result.evaluated_at == BASE_TIME


def test_returns_stale_host() -> None:
    """Return STALE at the configured boundary."""
    host = HostRecord.register(
        build_heartbeat()
    )
    registry = FakeHostRegistry((host,))
    evaluated_at = BASE_TIME + timedelta(seconds=30)

    result = build_service(
        registry,
        current_time=evaluated_at,
    ).get_by_id("host-001")

    assert result is not None
    assert result.availability is HostAvailability.STALE
    assert result.heartbeat_age_seconds == 30


def test_returns_offline_host() -> None:
    """Return OFFLINE at the configured boundary."""
    host = HostRecord.register(
        build_heartbeat()
    )
    registry = FakeHostRegistry((host,))
    evaluated_at = BASE_TIME + timedelta(seconds=120)

    result = build_service(
        registry,
        current_time=evaluated_at,
    ).get_by_id("host-001")

    assert result is not None
    assert result.availability is HostAvailability.OFFLINE
    assert result.heartbeat_age_seconds == 120


def test_returns_none_for_unknown_host() -> None:
    """Return None when the host is not registered."""
    service = build_service(FakeHostRegistry())

    assert service.get_by_id("missing-host") is None


def test_lists_hosts_using_same_evaluation_time() -> None:
    """Evaluate every listed host at one shared time."""
    first = HostRecord.register(
        build_heartbeat(
            host_id="host-001",
            observed_at=BASE_TIME,
        )
    )
    second = HostRecord.register(
        build_heartbeat(
            host_id="host-002",
            observed_at=(
                BASE_TIME + timedelta(seconds=100)
            ),
        )
    )

    evaluated_at = BASE_TIME + timedelta(seconds=130)
    service = build_service(
        FakeHostRegistry((first, second)),
        current_time=evaluated_at,
    )

    results = service.list_all()

    assert len(results) == 2
    assert all(
        result.evaluated_at == evaluated_at
        for result in results
    )

    statuses = {
        result.host.host_id: result.availability
        for result in results
    }

    assert (
        statuses["host-001"]
        is HostAvailability.OFFLINE
    )
    assert (
        statuses["host-002"]
        is HostAvailability.STALE
    )


def test_rejects_naive_clock_value() -> None:
    """Require the injected clock to return aware time."""
    host = HostRecord.register(
        build_heartbeat()
    )
    registry = FakeHostRegistry((host,))

    service = HostRegistryService(
        registry=registry,
        evaluator=HostStatusEvaluator(
            HostAvailabilityPolicy(
                stale_after_seconds=30,
                offline_after_seconds=120,
            )
        ),
        clock=lambda: datetime(2026, 7, 20, 10, 0),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        service.get_by_id("host-001")
