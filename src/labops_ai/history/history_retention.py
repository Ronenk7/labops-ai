"""Apply automatic retention rules to persisted run history."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from labops_ai.history.history_config import (
    RunHistoryRetentionConfig,
)


class RunHistoryRetentionError(RuntimeError):
    """Represent a failure while pruning run history."""


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _normalize_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and normalize a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must contain timezone information."
        )

    return value.astimezone(timezone.utc)


def _normalize_deleted_count(
    field_name: str,
    value: object,
) -> int:
    """Validate a non-negative deleted-row count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(
            f"{field_name} must not be negative."
        )

    return value


@dataclass(frozen=True, slots=True)
class RunHistoryRetentionResult:
    """Summarize rows deleted by retention rules."""

    deleted_by_age: int
    deleted_by_count: int

    def __post_init__(self) -> None:
        """Validate deleted-row counts."""
        deleted_by_age = _normalize_deleted_count(
            "Deleted run count by age",
            self.deleted_by_age,
        )
        deleted_by_count = _normalize_deleted_count(
            "Deleted run count by maximum count",
            self.deleted_by_count,
        )

        object.__setattr__(
            self,
            "deleted_by_age",
            deleted_by_age,
        )
        object.__setattr__(
            self,
            "deleted_by_count",
            deleted_by_count,
        )

    @property
    def total_deleted(self) -> int:
        """Return the total number of deleted runs."""
        return (
            self.deleted_by_age
            + self.deleted_by_count
        )


@dataclass(frozen=True, slots=True)
class RunHistoryRetentionPolicy:
    """Delete runs exceeding configured retention limits."""

    config: RunHistoryRetentionConfig
    clock: Callable[[], datetime] = _utc_now

    def __post_init__(self) -> None:
        """Validate retention dependencies."""
        if not isinstance(
            self.config,
            RunHistoryRetentionConfig,
        ):
            raise TypeError(
                "config must be a "
                "RunHistoryRetentionConfig instance."
            )

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def prune(
        self,
        connection: sqlite3.Connection,
    ) -> RunHistoryRetentionResult:
        """Apply age and count limits without committing."""
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError(
                "connection must be a "
                "sqlite3.Connection instance."
            )

        reference_time = _normalize_aware_datetime(
            "Run history retention time",
            self.clock(),
        )

        try:
            deleted_by_age = self._delete_by_age(
                connection,
                reference_time,
            )
            deleted_by_count = self._delete_by_count(
                connection
            )
        except sqlite3.Error as error:
            raise RunHistoryRetentionError(
                "Run history retention could not be applied."
            ) from error

        return RunHistoryRetentionResult(
            deleted_by_age=deleted_by_age,
            deleted_by_count=deleted_by_count,
        )

    def _delete_by_age(
        self,
        connection: sqlite3.Connection,
        reference_time: datetime,
    ) -> int:
        """Delete runs older than the configured age."""
        if self.config.max_age_days is None:
            return 0

        cutoff_time = reference_time - timedelta(
            days=self.config.max_age_days
        )

        cursor = connection.execute(
            """
            DELETE FROM monitoring_runs
            WHERE generated_at < ?
            """,
            (cutoff_time.isoformat(),),
        )

        return self._row_count(cursor)

    def _delete_by_count(
        self,
        connection: sqlite3.Connection,
    ) -> int:
        """Keep only the most recently inserted runs."""
        cursor = connection.execute(
            """
            DELETE FROM monitoring_runs
            WHERE run_id IN (
                SELECT run_id
                FROM monitoring_runs
                ORDER BY run_id DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (self.config.max_runs,),
        )

        return self._row_count(cursor)

    @staticmethod
    def _row_count(
        cursor: sqlite3.Cursor,
    ) -> int:
        """Return a normalized SQLite affected-row count."""
        if cursor.rowcount < 0:
            return 0

        return cursor.rowcount
