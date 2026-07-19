"""Query persisted monitoring run history from SQLite."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from labops_ai.health_status import HealthStatus
from labops_ai.history.history_database import (
    RunHistoryDatabase,
    RunHistoryDatabaseError,
)
from labops_ai.history.history_models import (
    RunHistoryEntry,
)


_MAX_QUERY_LIMIT = 1000
_MAX_HOST_SUGGESTION_LIMIT = 20


class RunHistoryQueryError(RuntimeError):
    """Represent a failure while reading run history."""


def _normalize_positive_integer(
    field_name: str,
    value: object,
) -> int:
    """Validate one positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return value


def _normalize_limit(value: object) -> int:
    """Validate the maximum number of returned rows."""
    normalized_value = _normalize_positive_integer(
        "Run history query limit",
        value,
    )

    if normalized_value > _MAX_QUERY_LIMIT:
        raise ValueError(
            "Run history query limit must not exceed "
            f"{_MAX_QUERY_LIMIT}."
        )

    return normalized_value


def _normalize_host_suggestion_prefix(
    value: object,
) -> str:
    """Validate and normalize a host suggestion prefix."""
    if not isinstance(value, str):
        raise TypeError(
            "Host suggestion prefix must be a string."
        )

    return value.strip()


def _normalize_host_suggestion_limit(
    value: object,
) -> int:
    """Validate the host suggestion result limit."""
    normalized_value = _normalize_positive_integer(
        "Host suggestion limit",
        value,
    )

    if normalized_value > _MAX_HOST_SUGGESTION_LIMIT:
        raise ValueError(
            "Host suggestion limit must not exceed "
            f"{_MAX_HOST_SUGGESTION_LIMIT}."
        )

    return normalized_value


def _normalize_optional_host_name(
    value: object | None,
) -> str | None:
    """Validate and normalize an optional host name."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            "Run history host name must be a string or None."
        )

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            "Run history host name must not be empty."
        )

    return normalized_value


def _validate_optional_status(
    value: object | None,
) -> HealthStatus | None:
    """Validate an optional health status."""
    if value is None:
        return None

    if not isinstance(value, HealthStatus):
        raise TypeError(
            "Run history status must be a "
            "HealthStatus instance or None."
        )

    return value


@dataclass(frozen=True, slots=True)
class RunHistoryQuery:
    """Read validated monitoring summaries from SQLite."""

    database: RunHistoryDatabase

    def __post_init__(self) -> None:
        """Validate the database dependency."""
        if not isinstance(
            self.database,
            RunHistoryDatabase,
        ):
            raise TypeError(
                "database must be a "
                "RunHistoryDatabase instance."
            )

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        """Return one run by its identifier."""
        normalized_run_id = _normalize_positive_integer(
            "Run history ID",
            run_id,
        )

        row = self._fetch_one(
            """
            SELECT
                run_id,
                generated_at,
                host_name,
                overall_status,
                system_status,
                network_status,
                service_status,
                process_status,
                log_status,
                active_incident_count,
                resolved_incident_count,
                bundle_id,
                archive_path
            FROM monitoring_runs
            WHERE run_id = ?
            """,
            (normalized_run_id,),
        )

        if row is None:
            return None

        return self._row_to_entry(row)

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        """Return the newest stored monitoring run."""
        normalized_host_name = (
            _normalize_optional_host_name(host_name)
        )

        query = """
            SELECT
                run_id,
                generated_at,
                host_name,
                overall_status,
                system_status,
                network_status,
                service_status,
                process_status,
                log_status,
                active_incident_count,
                resolved_incident_count,
                bundle_id,
                archive_path
            FROM monitoring_runs
        """
        parameters: tuple[object, ...] = ()

        if normalized_host_name is not None:
            query += """
                WHERE host_name COLLATE NOCASE = ?
            """
            parameters = (normalized_host_name,)

        query += """
            ORDER BY
                generated_at DESC,
                run_id DESC
            LIMIT 1
        """

        row = self._fetch_one(
            query,
            parameters,
        )

        if row is None:
            return None

        return self._row_to_entry(row)

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        """Return recent runs using optional filters."""
        normalized_limit = _normalize_limit(limit)
        normalized_status = _validate_optional_status(
            status
        )
        normalized_host_name = (
            _normalize_optional_host_name(host_name)
        )

        conditions: list[str] = []
        parameters: list[object] = []

        if normalized_status is not None:
            conditions.append("overall_status = ?")
            parameters.append(normalized_status.value)

        if normalized_host_name is not None:
            conditions.append("host_name COLLATE NOCASE = ?")
            parameters.append(normalized_host_name)

        query = """
            SELECT
                run_id,
                generated_at,
                host_name,
                overall_status,
                system_status,
                network_status,
                service_status,
                process_status,
                log_status,
                active_incident_count,
                resolved_incident_count,
                bundle_id,
                archive_path
            FROM monitoring_runs
        """

        if conditions:
            query += (
                "\nWHERE "
                + " AND ".join(conditions)
            )

        query += """
            ORDER BY
                generated_at DESC,
                run_id DESC
            LIMIT ?
        """
        parameters.append(normalized_limit)

        rows = self._fetch_all(
            query,
            tuple(parameters),
        )

        return tuple(
            self._row_to_entry(row)
            for row in rows
        )


    def suggest_hosts(
        self,
        *,
        prefix: str = "",
        limit: int = 10,
    ) -> tuple[str, ...]:
        """Return recent distinct hosts matching a prefix."""
        normalized_prefix = (
            _normalize_host_suggestion_prefix(prefix)
        )
        normalized_limit = (
            _normalize_host_suggestion_limit(limit)
        )

        escaped_prefix = (
            normalized_prefix
            .replace("~", "~~")
            .replace("%", "~%")
            .replace("_", "~_")
        )

        rows = self._fetch_all(
            """
            SELECT
                host_name,
                MAX(generated_at) AS latest_generated_at
            FROM monitoring_runs
            WHERE host_name LIKE ? ESCAPE '~'
                COLLATE NOCASE
            GROUP BY host_name COLLATE NOCASE
            ORDER BY
                latest_generated_at DESC,
                host_name COLLATE NOCASE ASC
            LIMIT ?
            """,
            (
                f"{escaped_prefix}%",
                normalized_limit,
            ),
        )

        return tuple(
            str(row["host_name"])
            for row in rows
        )

    def count_runs(
        self,
        *,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> int:
        """Count stored runs using optional filters."""
        normalized_status = _validate_optional_status(
            status
        )
        normalized_host_name = (
            _normalize_optional_host_name(host_name)
        )

        conditions: list[str] = []
        parameters: list[object] = []

        if normalized_status is not None:
            conditions.append("overall_status = ?")
            parameters.append(normalized_status.value)

        if normalized_host_name is not None:
            conditions.append("host_name COLLATE NOCASE = ?")
            parameters.append(normalized_host_name)

        query = """
            SELECT COUNT(*) AS run_count
            FROM monitoring_runs
        """

        if conditions:
            query += (
                "\nWHERE "
                + " AND ".join(conditions)
            )

        row = self._fetch_one(
            query,
            tuple(parameters),
        )

        if row is None:
            raise RunHistoryQueryError(
                "SQLite did not return a run count."
            )

        return int(row["run_count"])

    def _fetch_one(
        self,
        query: str,
        parameters: tuple[object, ...],
    ) -> sqlite3.Row | None:
        """Execute one query and return its first row."""
        connection = self._open_connection()

        try:
            return connection.execute(
                query,
                parameters,
            ).fetchone()
        except sqlite3.Error as error:
            raise RunHistoryQueryError(
                "Run history query could not be completed."
            ) from error
        finally:
            connection.close()

    def _fetch_all(
        self,
        query: str,
        parameters: tuple[object, ...],
    ) -> tuple[sqlite3.Row, ...]:
        """Execute one query and return all rows."""
        connection = self._open_connection()

        try:
            return tuple(
                connection.execute(
                    query,
                    parameters,
                ).fetchall()
            )
        except sqlite3.Error as error:
            raise RunHistoryQueryError(
                "Run history query could not be completed."
            ) from error
        finally:
            connection.close()

    def _open_connection(
        self,
    ) -> sqlite3.Connection:
        """Initialize and open the history database."""
        try:
            self.database.initialize()
            return self.database.connect()
        except RunHistoryDatabaseError as error:
            raise RunHistoryQueryError(
                "Run history database could not be prepared."
            ) from error

    @staticmethod
    def _row_to_entry(
        row: sqlite3.Row,
    ) -> RunHistoryEntry:
        """Convert one SQLite row into a validated model."""
        try:
            return RunHistoryEntry(
                run_id=int(row["run_id"]),
                generated_at=datetime.fromisoformat(
                    str(row["generated_at"])
                ),
                host_name=str(row["host_name"]),
                overall_status=HealthStatus(
                    row["overall_status"]
                ),
                system_status=HealthStatus(
                    row["system_status"]
                ),
                network_status=HealthStatus(
                    row["network_status"]
                ),
                service_status=HealthStatus(
                    row["service_status"]
                ),
                process_status=HealthStatus(
                    row["process_status"]
                ),
                log_status=HealthStatus(
                    row["log_status"]
                ),
                active_incident_count=int(
                    row["active_incident_count"]
                ),
                resolved_incident_count=int(
                    row["resolved_incident_count"]
                ),
                bundle_id=str(row["bundle_id"]),
                archive_path=str(row["archive_path"]),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            raise RunHistoryQueryError(
                "Run history contains an invalid "
                "monitoring run record."
            ) from error
