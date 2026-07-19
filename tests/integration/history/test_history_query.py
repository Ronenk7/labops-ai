"""Integration tests for SQLite run history queries."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryDatabase,
    RunHistoryQuery,
    RunHistoryQueryError,
    RunHistoryStorageConfig,
    RunHistoryStore,
)
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "history/history_query_cases.json"
)


def build_history_components(
    tmp_path: Path,
) -> tuple[RunHistoryStore, RunHistoryQuery]:
    """Build history storage and query components."""
    database = RunHistoryDatabase(
        config=RunHistoryStorageConfig(
            database_path=str(
                tmp_path / "run_history.sqlite3"
            ),
            busy_timeout_seconds=5.0,
        )
    )

    return (
        RunHistoryStore(database=database),
        RunHistoryQuery(database=database),
    )


def seed_history(
    store: RunHistoryStore,
) -> None:
    """Persist three deterministic monitoring runs."""
    base_snapshot = build_test_diagnostic_snapshot()

    snapshots = (
        replace(
            base_snapshot,
            generated_at=datetime.fromisoformat(
                "2026-07-19T10:30:00+00:00"
            ),
            host_name="Kukner7",
        ),
        replace(
            base_snapshot,
            generated_at=datetime.fromisoformat(
                "2026-07-19T10:35:00+00:00"
            ),
            host_name="LabHost",
            system_overall_status=HealthStatus.WARNING,
            network_overall_status=HealthStatus.WARNING,
            service_overall_status=HealthStatus.WARNING,
            process_overall_status=HealthStatus.WARNING,
            log_overall_status=HealthStatus.WARNING,
        ),
        replace(
            base_snapshot,
            generated_at=datetime.fromisoformat(
                "2026-07-19T10:40:00+00:00"
            ),
            host_name="Kukner7",
            system_overall_status=HealthStatus.HEALTHY,
            network_overall_status=HealthStatus.HEALTHY,
            service_overall_status=HealthStatus.HEALTHY,
            process_overall_status=HealthStatus.HEALTHY,
            log_overall_status=HealthStatus.HEALTHY,
        ),
    )

    for snapshot, run_case in zip(
        snapshots,
        CASES["runs"],
        strict=True,
    ):
        store.save(
            snapshot,
            bundle_id=run_case["bundle_id"],
            archive_path=run_case["archive_path"],
        )


class TestRunHistoryQuery:
    """Test validated run history retrieval."""

    def test_rejects_invalid_database_dependency(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="RunHistoryDatabase",
        ):
            RunHistoryQuery(database=object())

    def test_empty_database_returns_empty_results(
        self,
        tmp_path: Path,
    ) -> None:
        _, query = build_history_components(tmp_path)

        assert query.get_latest() is None
        assert query.get_by_id(1) is None
        assert query.list_recent() == ()
        assert query.count_runs() == 0

    def test_gets_run_by_identifier(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entry = query.get_by_id(2)

        assert entry is not None
        assert entry.run_id == 2
        assert entry.bundle_id == "bundle-002"
        assert entry.host_name == "LabHost"
        assert entry.overall_status is HealthStatus.WARNING

    def test_returns_none_for_missing_run_identifier(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        assert query.get_by_id(999) is None

    def test_gets_latest_run(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entry = query.get_latest()

        assert entry is not None
        assert entry.run_id == 3
        assert entry.bundle_id == "bundle-003"
        assert entry.overall_status is HealthStatus.HEALTHY

    def test_gets_latest_run_for_host(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entry = query.get_latest(host_name=" LabHost ")

        assert entry is not None
        assert entry.run_id == 2
        assert entry.host_name == "LabHost"

    def test_lists_runs_newest_first(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entries = query.list_recent()

        assert tuple(
            entry.bundle_id
            for entry in entries
        ) == (
            "bundle-003",
            "bundle-002",
            "bundle-001",
        )

    def test_applies_result_limit(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entries = query.list_recent(limit=2)

        assert tuple(
            entry.run_id
            for entry in entries
        ) == (3, 2)

    def test_filters_runs_by_status(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entries = query.list_recent(
            status=HealthStatus.CRITICAL
        )

        assert len(entries) == 1
        assert entries[0].bundle_id == "bundle-001"

    def test_filters_runs_by_host(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entries = query.list_recent(
            host_name="Kukner7"
        )

        assert tuple(
            entry.run_id
            for entry in entries
        ) == (3, 1)

    def test_combines_status_and_host_filters(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        entries = query.list_recent(
            status=HealthStatus.HEALTHY,
            host_name="Kukner7",
        )

        assert len(entries) == 1
        assert entries[0].run_id == 3

    def test_counts_runs_using_filters(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        assert query.count_runs() == 3
        assert query.count_runs(
            status=HealthStatus.WARNING
        ) == 1
        assert query.count_runs(
            host_name="Kukner7"
        ) == 2
        assert query.count_runs(
            status=HealthStatus.HEALTHY,
            host_name="Kukner7",
        ) == 1

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_run_ids"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_run_identifier(
        self,
        tmp_path: Path,
        case: dict[str, object],
    ) -> None:
        _, query = build_history_components(tmp_path)
        value = case["value"]

        expected_error = (
            TypeError
            if isinstance(value, (str, bool))
            else ValueError
        )

        with pytest.raises(expected_error):
            query.get_by_id(value)

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_limits"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_limit(
        self,
        tmp_path: Path,
        case: dict[str, object],
    ) -> None:
        _, query = build_history_components(tmp_path)
        value = case["value"]

        expected_error = (
            TypeError
            if isinstance(value, (str, bool))
            else ValueError
        )

        with pytest.raises(expected_error):
            query.list_recent(limit=value)

    @pytest.mark.parametrize(
        "host_name, expected_error",
        (
            (" ", ValueError),
            (123, TypeError),
        ),
        ids=(
            "empty-host",
            "non-string-host",
        ),
    )
    def test_rejects_invalid_host_name(
        self,
        tmp_path: Path,
        host_name: object,
        expected_error: type[Exception],
    ) -> None:
        _, query = build_history_components(tmp_path)

        with pytest.raises(expected_error):
            query.list_recent(host_name=host_name)

    def test_rejects_invalid_status_filter(
        self,
        tmp_path: Path,
    ) -> None:
        _, query = build_history_components(tmp_path)

        with pytest.raises(
            TypeError,
            match="HealthStatus",
        ):
            query.list_recent(status="CRITICAL")

    def test_reports_invalid_persisted_record(
        self,
        tmp_path: Path,
    ) -> None:
        store, query = build_history_components(tmp_path)
        seed_history(store)

        connection = store.database.connect()
        try:
            connection.execute(
                """
                UPDATE monitoring_runs
                SET generated_at = 'invalid-datetime'
                WHERE run_id = 1
                """
            )
            connection.commit()
        finally:
            connection.close()

        with pytest.raises(
            RunHistoryQueryError,
            match="invalid monitoring run record",
        ):
            query.get_by_id(1)
