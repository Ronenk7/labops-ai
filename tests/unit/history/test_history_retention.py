"""Unit tests for automatic run history retention."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from labops_ai.history import (
    RunHistoryDatabase,
    RunHistoryStorageConfig,
    RunHistoryStore,
)
from labops_ai.history.history_config import (
    RunHistoryRetentionConfig,
)
from labops_ai.history.history_retention import (
    RunHistoryRetentionError,
    RunHistoryRetentionPolicy,
    RunHistoryRetentionResult,
)
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "history/history_retention_cases.json"
)


def build_database(
    tmp_path: Path,
) -> RunHistoryDatabase:
    """Build a temporary initialized history database."""
    return RunHistoryDatabase(
        config=RunHistoryStorageConfig(
            database_path=str(
                tmp_path / "run_history.sqlite3"
            ),
            busy_timeout_seconds=5.0,
        )
    )


def seed_history(
    database: RunHistoryDatabase,
) -> None:
    """Persist deterministic runs used by retention tests."""
    store = RunHistoryStore(database=database)
    base_snapshot = build_test_diagnostic_snapshot()

    for run_case in CASES["runs"]:
        snapshot = replace(
            base_snapshot,
            generated_at=datetime.fromisoformat(
                run_case["generated_at"]
            ),
        )

        store.save(
            snapshot,
            bundle_id=run_case["bundle_id"],
            archive_path=run_case["archive_path"],
        )


def build_policy(
    *,
    max_runs: int,
    max_age_days: int | None,
) -> RunHistoryRetentionPolicy:
    """Build a retention policy with a deterministic clock."""
    return RunHistoryRetentionPolicy(
        config=RunHistoryRetentionConfig(
            max_runs=max_runs,
            max_age_days=max_age_days,
            prune_on_write=True,
        ),
        clock=lambda: datetime.fromisoformat(
            CASES["reference_time"]
        ),
    )


def query_run_ids(
    database: RunHistoryDatabase,
) -> tuple[int, ...]:
    """Return all remaining run IDs in insertion order."""
    connection = database.connect()

    try:
        return tuple(
            row["run_id"]
            for row in connection.execute(
                """
                SELECT run_id
                FROM monitoring_runs
                ORDER BY run_id
                """
            )
        )
    finally:
        connection.close()


def query_count(
    database: RunHistoryDatabase,
    table_name: str,
) -> int:
    """Return the row count of one known history table."""
    connection = database.connect()

    try:
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()
    finally:
        connection.close()

    return int(row[0])


class TestRunHistoryRetentionResult:
    """Test retention result validation."""

    def test_accepts_valid_deleted_counts(
        self,
    ) -> None:
        result = RunHistoryRetentionResult(
            deleted_by_age=2,
            deleted_by_count=3,
        )

        assert result.deleted_by_age == 2
        assert result.deleted_by_count == 3
        assert result.total_deleted == 5

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_deleted_counts"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_deleted_counts(
        self,
        case: dict[str, Any],
    ) -> None:
        values = (
            case["deleted_by_age"],
            case["deleted_by_count"],
        )

        expected_error = (
            TypeError
            if any(
                isinstance(value, (str, bool))
                for value in values
            )
            else ValueError
        )

        with pytest.raises(expected_error):
            RunHistoryRetentionResult(
                deleted_by_age=case[
                    "deleted_by_age"
                ],
                deleted_by_count=case[
                    "deleted_by_count"
                ],
            )


class TestRunHistoryRetentionPolicy:
    """Test SQLite run history pruning."""

    def test_rejects_invalid_configuration(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="RunHistoryRetentionConfig",
        ):
            RunHistoryRetentionPolicy(
                config=object()
            )

    def test_rejects_non_callable_clock(
        self,
    ) -> None:
        config = RunHistoryRetentionConfig(
            max_runs=10,
            max_age_days=30,
            prune_on_write=True,
        )

        with pytest.raises(
            TypeError,
            match="clock must be callable",
        ):
            RunHistoryRetentionPolicy(
                config=config,
                clock=object(),
            )

    def test_rejects_invalid_connection(
        self,
    ) -> None:
        policy = build_policy(
            max_runs=10,
            max_age_days=30,
        )

        with pytest.raises(
            TypeError,
            match="sqlite3.Connection",
        ):
            policy.prune(object())

    def test_deletes_runs_older_than_maximum_age(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=10,
            max_age_days=30,
        )

        connection = database.connect()

        try:
            result = policy.prune(connection)
            connection.commit()
        finally:
            connection.close()

        assert result.deleted_by_age == 1
        assert result.deleted_by_count == 0
        assert result.total_deleted == 1
        assert query_run_ids(database) == (2, 3, 4)

    def test_keeps_only_maximum_run_count(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=2,
            max_age_days=None,
        )

        connection = database.connect()

        try:
            result = policy.prune(connection)
            connection.commit()
        finally:
            connection.close()

        assert result.deleted_by_age == 0
        assert result.deleted_by_count == 2
        assert result.total_deleted == 2
        assert query_run_ids(database) == (3, 4)

    def test_applies_age_before_count_limit(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=2,
            max_age_days=30,
        )

        connection = database.connect()

        try:
            result = policy.prune(connection)
            connection.commit()
        finally:
            connection.close()

        assert result.deleted_by_age == 1
        assert result.deleted_by_count == 1
        assert result.total_deleted == 2
        assert query_run_ids(database) == (3, 4)

    def test_returns_zero_when_no_runs_exceed_limits(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=10,
            max_age_days=365,
        )

        connection = database.connect()

        try:
            result = policy.prune(connection)
            connection.commit()
        finally:
            connection.close()

        assert result.deleted_by_age == 0
        assert result.deleted_by_count == 0
        assert result.total_deleted == 0
        assert query_run_ids(database) == (1, 2, 3, 4)

    def test_cascade_deletes_child_records(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=2,
            max_age_days=30,
        )

        connection = database.connect()

        try:
            policy.prune(connection)
            connection.commit()
        finally:
            connection.close()

        assert query_count(
            database,
            "monitoring_runs",
        ) == 2
        assert query_count(
            database,
            "system_metrics",
        ) == 4
        assert query_count(
            database,
            "network_checks",
        ) == 4
        assert query_count(
            database,
            "incident_snapshots",
        ) == 4

    def test_does_not_commit_automatically(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        seed_history(database)
        policy = build_policy(
            max_runs=2,
            max_age_days=None,
        )

        connection = database.connect()

        try:
            policy.prune(connection)

            current_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM monitoring_runs
                """
            ).fetchone()[0]

            assert current_count == 2

            connection.rollback()
        finally:
            connection.close()

        assert query_count(
            database,
            "monitoring_runs",
        ) == 4

    def test_rejects_clock_without_timezone(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        database.initialize()

        policy = RunHistoryRetentionPolicy(
            config=RunHistoryRetentionConfig(
                max_runs=10,
                max_age_days=30,
                prune_on_write=True,
            ),
            clock=lambda: datetime(
                2026,
                7,
                20,
                12,
                0,
            ),
        )

        connection = database.connect()

        try:
            with pytest.raises(
                ValueError,
                match="timezone information",
            ):
                policy.prune(connection)
        finally:
            connection.close()

    def test_wraps_sqlite_failure(
        self,
    ) -> None:
        policy = build_policy(
            max_runs=2,
            max_age_days=None,
        )
        connection = sqlite3.connect(":memory:")

        try:
            with pytest.raises(
                RunHistoryRetentionError,
                match="could not be applied",
            ):
                policy.prune(connection)
        finally:
            connection.close()
