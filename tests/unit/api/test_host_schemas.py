"""Tests for monitored-host API contracts."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from labops_ai.api.host_schemas import (
    HostHeartbeatRequest,
    HostResponse,
)
from labops_ai.hosts import (
    HostAvailability,
    HostHeartbeat,
    HostRecord,
    HostStatusSnapshot,
)


pytestmark = pytest.mark.unit

OBSERVED_AT = datetime(
    2026,
    7,
    20,
    11,
    30,
    tzinfo=timezone.utc,
)


def build_request() -> HostHeartbeatRequest:
    """Create one valid heartbeat request."""
    return HostHeartbeatRequest(
        host_id=" host-001 ",
        host_name=" lab-node-01 ",
        address=" 10.0.0.10 ",
        operating_system=" Ubuntu 24.04 ",
        architecture=" x86_64 ",
        agent_version=" 0.1.0 ",
        observed_at=OBSERVED_AT,
    )


def test_converts_request_to_domain_heartbeat() -> None:
    """Normalize request values and create the domain model."""
    request = build_request()

    heartbeat = request.to_domain()

    assert heartbeat == HostHeartbeat(
        host_id="host-001",
        host_name="lab-node-01",
        address="10.0.0.10",
        operating_system="Ubuntu 24.04",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=OBSERVED_AT,
    )


def test_rejects_naive_observed_at() -> None:
    """Require a timezone-aware heartbeat timestamp."""
    with pytest.raises(
        ValidationError,
        match="timezone-aware",
    ):
        HostHeartbeatRequest(
            host_id="host-001",
            host_name="lab-node-01",
            address="10.0.0.10",
            operating_system="Ubuntu 24.04",
            architecture="x86_64",
            agent_version="0.1.0",
            observed_at=datetime(2026, 7, 20, 11, 30),
        )


def test_rejects_unknown_request_field() -> None:
    """Reject unsupported heartbeat properties."""
    payload = build_request().model_dump()
    payload["unexpected"] = True

    with pytest.raises(
        ValidationError,
        match="Extra inputs are not permitted",
    ):
        HostHeartbeatRequest(**payload)


def test_converts_status_snapshot_to_response() -> None:
    """Expose host identity and calculated availability."""
    heartbeat = build_request().to_domain()
    host = HostRecord.register(heartbeat)

    snapshot = HostStatusSnapshot(
        host=host,
        availability=HostAvailability.ONLINE,
        evaluated_at=OBSERVED_AT,
        heartbeat_age_seconds=0,
    )

    response = HostResponse.from_snapshot(snapshot)

    assert response.host_id == "host-001"
    assert response.host_name == "lab-node-01"
    assert response.availability is HostAvailability.ONLINE
    assert response.registered_at == OBSERVED_AT
    assert response.last_seen_at == OBSERVED_AT
    assert response.heartbeat_age_seconds == 0


def test_rejects_invalid_snapshot_type() -> None:
    """Require the domain status-snapshot type."""
    with pytest.raises(
        TypeError,
        match="HostStatusSnapshot",
    ):
        HostResponse.from_snapshot(object())
