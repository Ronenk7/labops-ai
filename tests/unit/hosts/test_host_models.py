"""Tests for host registry domain models."""
from datetime import datetime, timedelta, timezone

import pytest

from labops_ai.hosts import (
    HostAvailability,
    HostHeartbeat,
    HostRecord,
)


pytestmark = pytest.mark.unit

NOW = datetime(
    2026,
    7,
    20,
    10,
    0,
    tzinfo=timezone.utc,
)


def build_heartbeat(
    *,
    host_id: str = "host-kukner7",
    observed_at: datetime = NOW,
) -> HostHeartbeat:
    """Build one deterministic host heartbeat."""
    return HostHeartbeat(
        host_id=host_id,
        host_name="Kukner7",
        address="192.168.1.50",
        operating_system="Ubuntu 24.04",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=observed_at,
    )


def test_registers_host_from_first_heartbeat() -> None:
    heartbeat = build_heartbeat()

    record = HostRecord.register(heartbeat)

    assert record.host_id == "host-kukner7"
    assert record.host_name == "Kukner7"
    assert record.registered_at == NOW
    assert record.last_seen_at == NOW


def test_applies_newer_heartbeat() -> None:
    original = HostRecord.register(
        build_heartbeat()
    )
    next_time = NOW + timedelta(seconds=10)

    updated = original.apply_heartbeat(
        HostHeartbeat(
            host_id="host-kukner7",
            host_name="Kukner7",
            address="192.168.1.60",
            operating_system="Ubuntu 24.04",
            architecture="x86_64",
            agent_version="0.2.0",
            observed_at=next_time,
        )
    )

    assert updated.address == "192.168.1.60"
    assert updated.agent_version == "0.2.0"
    assert updated.last_seen_at == next_time
    assert updated.registered_at == NOW


def test_rejects_heartbeat_for_different_host() -> None:
    record = HostRecord.register(
        build_heartbeat()
    )

    with pytest.raises(
        ValueError,
        match="host_id does not match",
    ):
        record.apply_heartbeat(
            build_heartbeat(
                host_id="different-host"
            )
        )


def test_rejects_older_heartbeat() -> None:
    record = HostRecord.register(
        build_heartbeat()
    )

    with pytest.raises(
        ValueError,
        match="older than",
    ):
        record.apply_heartbeat(
            build_heartbeat(
                observed_at=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_rejects_naive_timestamp() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        build_heartbeat(
            observed_at=datetime(2026, 7, 20)
        )


def test_normalizes_text_values() -> None:
    heartbeat = HostHeartbeat(
        host_id=" host-1 ",
        host_name=" server-one ",
        address=" 10.0.0.10 ",
        operating_system=" Ubuntu ",
        architecture=" x86_64 ",
        agent_version=" 0.1.0 ",
        observed_at=NOW,
    )

    assert heartbeat.host_id == "host-1"
    assert heartbeat.host_name == "server-one"
    assert heartbeat.address == "10.0.0.10"


def test_host_availability_values() -> None:
    assert HostAvailability.ONLINE == "ONLINE"
    assert HostAvailability.STALE == "STALE"
    assert HostAvailability.OFFLINE == "OFFLINE"
