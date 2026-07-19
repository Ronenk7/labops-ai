"""Integration tests for the SQLite run history database."""
from __future__ import annotations

from pathlib import Path

import pytest

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.history import (
    RunHistoryDatabase,
    RunHistoryDatabaseError,
    RunHistorySchemaError,
    RunHistoryStorageConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "history/history_database_cases.json"
)


def build_database(
    tmp_path: Path,
) -> RunHistoryDatabase:
    """Build a database using a temporary SQLite file."""
    return RunHistoryDatabase(
        config=RunHistoryStorageConfig(
            database_path=str(
                tmp_path / "run_history.sqlite3"
            ),
            busy_timeout_seconds=5.0,
        )
    )


class TestRunHistoryDatabase:
    """Test SQLite connection and schema management."""

    def test_rejects_invalid_configuration(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="RunHistoryStorageConfig",
        ):
            RunHistoryDatabase(config=object())

    def test_resolves_relative_database_path(
        self,
    ) -> None:
        database = RunHistoryDatabase(
            config=RunHistoryStorageConfig(
                database_path=(
                    "runtime/run_history.sqlite3"
                ),
                busy_timeout_seconds=5.0,
            )
        )

        assert database.path == (
            PROJECT_ROOT
            / "runtime"
            / "run_history.sqlite3"
        )

    def test_initializes_expected_schema(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)

        database.initialize()

        connection = database.connect()
        try:
            table_names = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                )
            }
            index_names = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'index'
                    """
                )
            }
            version_row = connection.execute(
                """
                SELECT value
                FROM history_metadata
                WHERE key = 'schema_version'
                """
            ).fetchone()
        finally:
            connection.close()

        assert set(
            CASES["expected_tables"]
        ).issubset(table_names)
        assert set(
            CASES["expected_indexes"]
        ).issubset(index_names)
        assert version_row is not None
        assert version_row["value"] == (
            CASES["schema_version"]
        )

    def test_applies_required_connection_settings(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        database.initialize()

        connection = database.connect()
        try:
            foreign_keys = connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()[0]
            journal_mode = connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
            busy_timeout = connection.execute(
                "PRAGMA busy_timeout"
            ).fetchone()[0]
            synchronous = connection.execute(
                "PRAGMA synchronous"
            ).fetchone()[0]
        finally:
            connection.close()

        assert foreign_keys == 1
        assert str(journal_mode).casefold() == "wal"
        assert busy_timeout == (
            CASES["busy_timeout_milliseconds"]
        )
        assert synchronous == 1

    def test_initialization_is_idempotent(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)

        database.initialize()
        database.initialize()

        assert database.path.is_file()

    def test_rejects_unsupported_schema_version(
        self,
        tmp_path: Path,
    ) -> None:
        database = build_database(tmp_path)
        database.initialize()

        connection = database.connect()
        try:
            connection.execute(
                """
                UPDATE history_metadata
                SET value = '999'
                WHERE key = 'schema_version'
                """
            )
            connection.commit()
        finally:
            connection.close()

        with pytest.raises(
            RunHistorySchemaError,
            match="Expected 1, found 999",
        ):
            database.initialize()

    def test_reports_invalid_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        blocked_parent = tmp_path / "blocked"
        blocked_parent.write_text(
            "This path is a file.",
            encoding="utf-8",
        )

        database = RunHistoryDatabase(
            config=RunHistoryStorageConfig(
                database_path=str(
                    blocked_parent / "history.sqlite3"
                ),
                busy_timeout_seconds=5.0,
            )
        )

        with pytest.raises(
            RunHistoryDatabaseError,
            match="could not be opened",
        ):
            database.initialize()
