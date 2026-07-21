"""Tests for the SQLite host registry."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from labops_ai.hosts import (
    HostHeartbeat,
    HostRegistrySchemaError,
    SqliteHostRegistry,
)


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    20,
    9,
    0,
    tzinfo=timezone.utc,
)


def build_heartbeat(
    *,
    host_id: str = "host-001",
    host_name: str = "lab-node-01",
    address: str = "10.0.0.10",
    operating_system: str = "Ubuntu 24.04",
    architecture: str = "x86_64",
    agent_version: str = "0.1.0",
    observed_at: datetime = BASE_TIME,
) -> HostHeartbeat:
    """Build one deterministic host heartbeat."""
    return HostHeartbeat(
        host_id=host_id,
        host_name=host_name,
        address=address,
        operating_system=operating_system,
        architecture=architecture,
        agent_version=agent_version,
        observed_at=observed_at,
    )


def test_initializes_registry_schema(tmp_path) -> None:
    """Create the registry tables and schema version."""
    database_path = tmp_path / "hosts.db"
    registry = SqliteHostRegistry(database_path)

    registry.initialize()

    connection = sqlite3.connect(database_path)

    try:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        version = connection.execute(
            """
            SELECT value
            FROM host_registry_metadata
            WHERE key = 'schema_version'
            """
        ).fetchone()
    finally:
        connection.close()

    assert "monitored_hosts" in table_names
    assert "host_registry_metadata" in table_names
    assert version == ("1",)


def test_registers_first_heartbeat(tmp_path) -> None:
    """Create a new host from its first heartbeat."""
    registry = SqliteHostRegistry(
        tmp_path / "hosts.db"
    )
    heartbeat = build_heartbeat()

    record = registry.record_heartbeat(heartbeat)

    assert record.host_id == heartbeat.host_id
    assert record.host_name == heartbeat.host_name
    assert record.registered_at == BASE_TIME
    assert record.last_seen_at == BASE_TIME
    assert registry.get_by_id(" host-001 ") == record


def test_updates_existing_host_and_preserves_registration(
    tmp_path,
) -> None:
    """Update mutable host data without changing registration."""
    registry = SqliteHostRegistry(
        tmp_path / "hosts.db"
    )

    original = registry.record_heartbeat(
        build_heartbeat()
    )

    later_time = BASE_TIME + timedelta(minutes=5)

    updated = registry.record_heartbeat(
        build_heartbeat(
            host_name="lab-node-renamed",
            address="10.0.0.20",
            operating_system="Ubuntu 26.04",
            agent_version="0.2.0",
            observed_at=later_time,
        )
    )

    assert updated.registered_at == original.registered_at
    assert updated.last_seen_at == later_time
    assert updated.host_name == "lab-node-renamed"
    assert updated.address == "10.0.0.20"
    assert updated.operating_system == "Ubuntu 26.04"
    assert updated.agent_version == "0.2.0"

    stored = registry.get_by_id("host-001")

    assert stored == updated


def test_rejects_older_heartbeat(tmp_path) -> None:
    """Prevent an old heartbeat from replacing newer data."""
    registry = SqliteHostRegistry(
        tmp_path / "hosts.db"
    )

    latest_time = BASE_TIME + timedelta(minutes=10)

    latest = registry.record_heartbeat(
        build_heartbeat(
            observed_at=latest_time,
        )
    )

    with pytest.raises(
        ValueError,
        match="older than",
    ):
        registry.record_heartbeat(
            build_heartbeat(
                host_name="outdated-name",
                observed_at=BASE_TIME,
            )
        )

    assert registry.get_by_id("host-001") == latest


def test_returns_none_for_unknown_host(tmp_path) -> None:
    """Return None when the host ID is not registered."""
    registry = SqliteHostRegistry(
        tmp_path / "hosts.db"
    )

    assert registry.get_by_id("missing-host") is None


def test_lists_hosts_by_latest_activity(tmp_path) -> None:
    """Order hosts by recent activity and then by name."""
    registry = SqliteHostRegistry(
        tmp_path / "hosts.db"
    )

    registry.record_heartbeat(
        build_heartbeat(
            host_id="host-old",
            host_name="Old Node",
            observed_at=BASE_TIME,
        )
    )

    latest_time = BASE_TIME + timedelta(minutes=5)

    registry.record_heartbeat(
        build_heartbeat(
            host_id="host-zulu",
            host_name="Zulu Node",
            observed_at=latest_time,
        )
    )

    registry.record_heartbeat(
        build_heartbeat(
            host_id="host-alpha",
            host_name="Alpha Node",
            observed_at=latest_time,
        )
    )

    hosts = registry.list_all()

    assert [
        host.host_id
        for host in hosts
    ] == [
        "host-alpha",
        "host-zulu",
        "host-old",
    ]


def test_rejects_unsupported_schema_version(
    tmp_path,
) -> None:
    """Reject a database created by another schema version."""
    database_path = tmp_path / "hosts.db"
    registry = SqliteHostRegistry(database_path)

    registry.initialize()

    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            UPDATE host_registry_metadata
            SET value = '999'
            WHERE key = 'schema_version'
            """
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        HostRegistrySchemaError,
        match="Expected 1, found 999",
    ):
        registry.initialize()
