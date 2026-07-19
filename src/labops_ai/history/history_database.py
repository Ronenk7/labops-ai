"""Create and configure the SQLite run history database."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.history.history_config import (
    RunHistoryStorageConfig,
)
from labops_ai.history.history_schema import (
    RUN_HISTORY_SCHEMA_SQL,
    RUN_HISTORY_SCHEMA_VERSION,
)


_SCHEMA_VERSION_KEY = "schema_version"


class RunHistoryDatabaseError(RuntimeError):
    """Represent a run history database failure."""


class RunHistorySchemaError(RunHistoryDatabaseError):
    """Represent an unsupported database schema version."""


@dataclass(frozen=True, slots=True)
class RunHistoryDatabase:
    """Manage SQLite connections and schema initialization."""

    config: RunHistoryStorageConfig

    def __post_init__(self) -> None:
        """Validate the database configuration dependency."""
        if not isinstance(
            self.config,
            RunHistoryStorageConfig,
        ):
            raise TypeError(
                "config must be a "
                "RunHistoryStorageConfig instance."
            )

    @property
    def path(self) -> Path:
        """Return the resolved SQLite database path."""
        configured_path = Path(
            self.config.database_path
        ).expanduser()

        if configured_path.is_absolute():
            return configured_path

        return PROJECT_ROOT / configured_path

    def connect(self) -> sqlite3.Connection:
        """Open and configure one SQLite connection."""
        connection: sqlite3.Connection | None = None

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            connection = sqlite3.connect(
                self.path,
                timeout=self.config.busy_timeout_seconds,
            )
            connection.row_factory = sqlite3.Row

            self._configure_connection(connection)

            return connection
        except (OSError, sqlite3.Error) as error:
            if connection is not None:
                connection.close()

            raise RunHistoryDatabaseError(
                "Run history database could not be opened: "
                f"{self.path}"
            ) from error

    def initialize(self) -> None:
        """Create and validate the complete database schema."""
        connection = self.connect()

        try:
            connection.executescript(
                RUN_HISTORY_SCHEMA_SQL
            )
            self._validate_schema_version(connection)
            connection.commit()
        except RunHistorySchemaError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise RunHistoryDatabaseError(
                "Run history schema could not be initialized: "
                f"{self.path}"
            ) from error
        finally:
            connection.close()

    def _configure_connection(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        """Apply required SQLite connection settings."""
        timeout_milliseconds = round(
            self.config.busy_timeout_seconds * 1000
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        connection.execute(
            f"PRAGMA busy_timeout = {timeout_milliseconds}"
        )

        journal_mode_row = connection.execute(
            "PRAGMA journal_mode = WAL"
        ).fetchone()

        if (
            journal_mode_row is None
            or str(journal_mode_row[0]).casefold() != "wal"
        ):
            raise sqlite3.OperationalError(
                "SQLite WAL journal mode could not be enabled."
            )

        connection.execute(
            "PRAGMA synchronous = NORMAL"
        )

    @staticmethod
    def _validate_schema_version(
        connection: sqlite3.Connection,
    ) -> None:
        """Create or validate the stored schema version."""
        row = connection.execute(
            """
            SELECT value
            FROM history_metadata
            WHERE key = ?
            """,
            (_SCHEMA_VERSION_KEY,),
        ).fetchone()

        expected_version = str(
            RUN_HISTORY_SCHEMA_VERSION
        )

        if row is None:
            connection.execute(
                """
                INSERT INTO history_metadata (
                    key,
                    value
                )
                VALUES (?, ?)
                """,
                (
                    _SCHEMA_VERSION_KEY,
                    expected_version,
                ),
            )
            return

        stored_version = str(row["value"])

        if stored_version != expected_version:
            raise RunHistorySchemaError(
                "Unsupported run history schema version. "
                f"Expected {expected_version}, "
                f"found {stored_version}."
            )
