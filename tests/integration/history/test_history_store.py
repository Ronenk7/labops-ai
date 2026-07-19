"""Integration tests for complete run history persistence."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryDatabase,
    RunHistoryStorageConfig,
    RunHistoryStore,
    RunHistoryStoreError,
)
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "history/history_store_cases.json"
)


def build_store(
    tmp_path: Path,
) -> RunHistoryStore:
    """Build a run history store using temporary SQLite."""
    database = RunHistoryDatabase(
        config=RunHistoryStorageConfig(
            database_path=str(
                tmp_path / "run_history.sqlite3"
            ),
            busy_timeout_seconds=5.0,
        )
    )
    return RunHistoryStore(database=database)


def query_count(
    store: RunHistoryStore,
    table_name: str,
) -> int:
    """Return the number of rows in one known table."""
    connection = store.database.connect()
    try:
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()
    finally:
        connection.close()

    return int(row[0])


class TestRunHistoryStore:
    """Test transactional diagnostic run persistence."""

    def test_rejects_invalid_database_dependency(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="RunHistoryDatabase",
        ):
            RunHistoryStore(database=object())

    def test_rejects_invalid_snapshot(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)

        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            store.save(
                object(),
                bundle_id=CASES["bundle_id"],
                archive_path=CASES["archive_path"],
            )

    def test_saves_complete_snapshot_and_returns_entry(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)
        snapshot = build_test_diagnostic_snapshot()

        entry = store.save(
            snapshot,
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )

        assert entry.run_id == 1
        assert entry.host_name == "Kukner7"
        assert entry.overall_status is (
            HealthStatus.CRITICAL
        )
        assert entry.active_incident_count == 1
        assert entry.resolved_incident_count == 1
        assert entry.incident_count == 2
        assert entry.bundle_id == CASES["bundle_id"]

    def test_saves_all_expected_child_records(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)

        store.save(
            build_test_diagnostic_snapshot(),
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )

        for table_name, expected_count in (
            CASES["expected_counts"].items()
        ):
            assert query_count(
                store,
                table_name,
            ) == expected_count

    def test_preserves_diagnostic_details(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)

        store.save(
            build_test_diagnostic_snapshot(),
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )

        connection = store.database.connect()
        try:
            network_row = connection.execute(
                """
                SELECT
                    latency_ms,
                    failure_reason,
                    error_message
                FROM network_checks
                WHERE check_type = 'TCP'
                """
            ).fetchone()

            process_row = connection.execute(
                """
                SELECT
                    instance_count,
                    total_cpu_percent,
                    total_memory_mb
                FROM process_checks
                WHERE process_name = 'python'
                """
            ).fetchone()

            pid_row = connection.execute(
                """
                SELECT pid
                FROM process_pids
                WHERE process_name = 'python'
                """
            ).fetchone()

            incident_row = connection.execute(
                """
                SELECT
                    status,
                    occurrence_count,
                    resolved_at
                FROM incident_snapshots
                WHERE incident_id = 'INC-000002'
                """
            ).fetchone()
        finally:
            connection.close()

        assert network_row["latency_ms"] is None
        assert network_row["failure_reason"] == (
            "TIMEOUT"
        )
        assert network_row["error_message"] == (
            "Connection timed out."
        )
        assert process_row["instance_count"] == 1
        assert process_row["total_cpu_percent"] == 75.5
        assert process_row["total_memory_mb"] == 450.25
        assert pid_row["pid"] == 100
        assert incident_row["status"] == "RESOLVED"
        assert incident_row["occurrence_count"] == 3
        assert incident_row["resolved_at"] is not None

    def test_assigns_sequential_run_ids(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)
        snapshot = build_test_diagnostic_snapshot()

        first_entry = store.save(
            snapshot,
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )
        second_entry = store.save(
            snapshot,
            bundle_id=CASES["second_bundle_id"],
            archive_path=CASES[
                "second_archive_path"
            ],
        )

        assert first_entry.run_id == 1
        assert second_entry.run_id == 2
        assert query_count(
            store,
            "monitoring_runs",
        ) == 2

    def test_rejects_duplicate_bundle_and_rolls_back(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)
        snapshot = build_test_diagnostic_snapshot()

        store.save(
            snapshot,
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )

        with pytest.raises(
            RunHistoryStoreError,
            match="could not be saved",
        ):
            store.save(
                snapshot,
                bundle_id=CASES["bundle_id"],
                archive_path=CASES["archive_path"],
            )

        assert query_count(
            store,
            "monitoring_runs",
        ) == 1
        assert query_count(
            store,
            "system_metrics",
        ) == 2

    def test_rolls_back_parent_when_child_insert_fails(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        store = build_store(tmp_path)

        def fail_insert(*args: Any, **kwargs: Any) -> None:
            raise sqlite3.OperationalError(
                "Forced child insert failure."
            )

        monkeypatch.setattr(
            RunHistoryStore,
            "_insert_network_checks",
            fail_insert,
        )

        with pytest.raises(
            RunHistoryStoreError,
            match="could not be saved",
        ):
            store.save(
                build_test_diagnostic_snapshot(),
                bundle_id=CASES["bundle_id"],
                archive_path=CASES["archive_path"],
            )

        assert query_count(
            store,
            "monitoring_runs",
        ) == 0
        assert query_count(
            store,
            "system_metrics",
        ) == 0

    def test_foreign_key_cascade_removes_child_records(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(tmp_path)

        entry = store.save(
            build_test_diagnostic_snapshot(),
            bundle_id=CASES["bundle_id"],
            archive_path=CASES["archive_path"],
        )

        connection = store.database.connect()
        try:
            connection.execute(
                """
                DELETE FROM monitoring_runs
                WHERE run_id = ?
                """,
                (entry.run_id,),
            )
            connection.commit()
        finally:
            connection.close()

        for table_name in (
            "system_metrics",
            "network_checks",
            "service_checks",
            "process_checks",
            "process_pids",
            "log_checks",
            "incident_snapshots",
        ):
            assert query_count(
                store,
                table_name,
            ) == 0
