"""Persist and query monitored hosts in SQLite."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.hosts.models import (
    HostHeartbeat,
    HostRecord,
)
from labops_ai.hosts.registry_schema import (
    HOST_REGISTRY_SCHEMA_SQL,
    HOST_REGISTRY_SCHEMA_VERSION,
)


_SCHEMA_VERSION_KEY = "schema_version"


class HostRegistryError(RuntimeError):
    """Represent a host-registry storage failure."""


class HostRegistrySchemaError(HostRegistryError):
    """Represent an unsupported registry schema version."""


def _normalize_host_id(value: object) -> str:
    """Validate and normalize a host identifier."""
    if not isinstance(value, str):
        raise TypeError("host_id must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError("host_id must not be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class SqliteHostRegistry:
    """Store the central host registry in SQLite."""

    database_path: str | Path
    busy_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        """Validate registry storage settings."""
        if not isinstance(
            self.database_path,
            (str, Path),
        ):
            raise TypeError(
                "database_path must be a string or Path."
            )

        if (
            isinstance(self.database_path, str)
            and not self.database_path.strip()
        ):
            raise ValueError(
                "database_path must not be empty."
            )

        if (
            isinstance(self.busy_timeout_seconds, bool)
            or not isinstance(
                self.busy_timeout_seconds,
                (int, float),
            )
        ):
            raise TypeError(
                "busy_timeout_seconds must be numeric."
            )

        if self.busy_timeout_seconds <= 0:
            raise ValueError(
                "busy_timeout_seconds must be positive."
            )

    @property
    def path(self) -> Path:
        """Return the resolved registry database path."""
        configured_path = Path(
            self.database_path
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
                timeout=self.busy_timeout_seconds,
            )
            connection.row_factory = sqlite3.Row

            timeout_milliseconds = round(
                self.busy_timeout_seconds * 1000
            )

            connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            connection.execute(
                f"PRAGMA busy_timeout = "
                f"{timeout_milliseconds}"
            )

            journal_mode = connection.execute(
                "PRAGMA journal_mode = WAL"
            ).fetchone()

            if (
                journal_mode is None
                or str(journal_mode[0]).casefold()
                != "wal"
            ):
                raise sqlite3.OperationalError(
                    "SQLite WAL mode could not be enabled."
                )

            connection.execute(
                "PRAGMA synchronous = NORMAL"
            )

            return connection
        except (OSError, sqlite3.Error) as error:
            if connection is not None:
                connection.close()

            raise HostRegistryError(
                "Host registry database could not "
                f"be opened: {self.path}"
            ) from error

    def initialize(self) -> None:
        """Create and validate the registry schema."""
        connection = self.connect()

        try:
            connection.executescript(
                HOST_REGISTRY_SCHEMA_SQL
            )
            self._validate_schema_version(connection)
            connection.commit()
        except HostRegistrySchemaError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise HostRegistryError(
                "Host registry schema could not "
                "be initialized."
            ) from error
        finally:
            connection.close()

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Create or update a host from one heartbeat."""
        if not isinstance(heartbeat, HostHeartbeat):
            raise TypeError(
                "heartbeat must be a HostHeartbeat."
            )

        self.initialize()
        connection = self.connect()

        try:
            connection.execute("BEGIN IMMEDIATE")

            current = self._select_by_id(
                connection,
                heartbeat.host_id,
            )

            record = (
                HostRecord.register(heartbeat)
                if current is None
                else current.apply_heartbeat(heartbeat)
            )

            connection.execute(
                """
                INSERT INTO monitored_hosts (
                    host_id,
                    host_name,
                    address,
                    operating_system,
                    architecture,
                    agent_version,
                    registered_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(host_id) DO UPDATE SET
                    host_name = excluded.host_name,
                    address = excluded.address,
                    operating_system =
                        excluded.operating_system,
                    architecture =
                        excluded.architecture,
                    agent_version =
                        excluded.agent_version,
                    last_seen_at =
                        excluded.last_seen_at
                """,
                (
                    record.host_id,
                    record.host_name,
                    record.address,
                    record.operating_system,
                    record.architecture,
                    record.agent_version,
                    record.registered_at.isoformat(),
                    record.last_seen_at.isoformat(),
                ),
            )

            connection.commit()
            return record
        except ValueError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise HostRegistryError(
                "Host heartbeat could not be stored."
            ) from error
        finally:
            connection.close()

    def get_by_id(
        self,
        host_id: str,
    ) -> HostRecord | None:
        """Return one registered host by ID."""
        normalized_id = _normalize_host_id(host_id)

        self.initialize()
        connection = self.connect()

        try:
            return self._select_by_id(
                connection,
                normalized_id,
            )
        except sqlite3.Error as error:
            raise HostRegistryError(
                "Host could not be read "
                "from the registry."
            ) from error
        finally:
            connection.close()

    def list_all(self) -> tuple[HostRecord, ...]:
        """Return all hosts ordered by recent activity."""
        self.initialize()
        connection = self.connect()

        try:
            rows = connection.execute(
                """
                SELECT
                    host_id,
                    host_name,
                    address,
                    operating_system,
                    architecture,
                    agent_version,
                    registered_at,
                    last_seen_at
                FROM monitored_hosts
                ORDER BY
                    last_seen_at DESC,
                    host_name COLLATE NOCASE ASC
                """
            ).fetchall()

            return tuple(
                self._row_to_record(row)
                for row in rows
            )
        except sqlite3.Error as error:
            raise HostRegistryError(
                "Hosts could not be listed "
                "from the registry."
            ) from error
        finally:
            connection.close()

    @staticmethod
    def _select_by_id(
        connection: sqlite3.Connection,
        host_id: str,
    ) -> HostRecord | None:
        """Read one host using an existing connection."""
        row = connection.execute(
            """
            SELECT
                host_id,
                host_name,
                address,
                operating_system,
                architecture,
                agent_version,
                registered_at,
                last_seen_at
            FROM monitored_hosts
            WHERE host_id = ?
            """,
            (host_id,),
        ).fetchone()

        if row is None:
            return None

        return SqliteHostRegistry._row_to_record(row)

    @staticmethod
    def _row_to_record(
        row: sqlite3.Row,
    ) -> HostRecord:
        """Convert one SQLite row into a domain record."""
        return HostRecord(
            host_id=str(row["host_id"]),
            host_name=str(row["host_name"]),
            address=str(row["address"]),
            operating_system=str(
                row["operating_system"]
            ),
            architecture=str(row["architecture"]),
            agent_version=str(row["agent_version"]),
            registered_at=datetime.fromisoformat(
                str(row["registered_at"])
            ),
            last_seen_at=datetime.fromisoformat(
                str(row["last_seen_at"])
            ),
        )

    @staticmethod
    def _validate_schema_version(
        connection: sqlite3.Connection,
    ) -> None:
        """Create or validate the schema version."""
        row = connection.execute(
            """
            SELECT value
            FROM host_registry_metadata
            WHERE key = ?
            """,
            (_SCHEMA_VERSION_KEY,),
        ).fetchone()

        expected_version = str(
            HOST_REGISTRY_SCHEMA_VERSION
        )

        if row is None:
            connection.execute(
                """
                INSERT INTO host_registry_metadata (
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
            raise HostRegistrySchemaError(
                "Unsupported host registry schema "
                f"version. Expected {expected_version}, "
                f"found {stored_version}."
            )
