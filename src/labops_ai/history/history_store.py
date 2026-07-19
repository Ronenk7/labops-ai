"""Persist complete diagnostic snapshots in SQLite."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from labops_ai.diagnostics import (
    DiagnosticIncidentRecord,
    DiagnosticLogRecord,
    DiagnosticNetworkCheck,
    DiagnosticProcessRecord,
    DiagnosticServiceRecord,
    DiagnosticSnapshot,
    DiagnosticSystemMetric,
)
from labops_ai.history.history_database import (
    RunHistoryDatabase,
    RunHistoryDatabaseError,
)
from labops_ai.history.history_models import (
    RunHistoryEntry,
)


class RunHistoryStoreError(RuntimeError):
    """Represent a failure while saving run history."""


def _normalize_bundle_id(value: object) -> str:
    """Validate and normalize a diagnostic bundle ID."""
    if not isinstance(value, str):
        raise TypeError("bundle_id must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError("bundle_id must not be empty.")

    return normalized_value


def _normalize_archive_path(
    value: object,
) -> str:
    """Validate and normalize a diagnostic ZIP path."""
    try:
        normalized_value = str(Path(value)).strip()
    except TypeError as error:
        raise TypeError(
            "archive_path must be path-compatible."
        ) from error

    if not normalized_value:
        raise ValueError(
            "archive_path must not be empty."
        )

    if Path(normalized_value).suffix.casefold() != ".zip":
        raise ValueError(
            "archive_path must use a .zip suffix."
        )

    return normalized_value


def _optional_enum_value(
    value: object | None,
) -> str | None:
    """Return an optional enumeration string value."""
    if value is None:
        return None

    return str(value.value)


def _optional_datetime_value(
    value: object | None,
) -> str | None:
    """Return an optional ISO-8601 datetime value."""
    if value is None:
        return None

    return value.isoformat()


@dataclass(frozen=True, slots=True)
class RunHistoryStore:
    """Persist complete monitoring runs transactionally."""

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

    def save(
        self,
        snapshot: DiagnosticSnapshot,
        *,
        bundle_id: str,
        archive_path: str | Path,
    ) -> RunHistoryEntry:
        """Persist one complete diagnostic run."""
        if not isinstance(snapshot, DiagnosticSnapshot):
            raise TypeError(
                "snapshot must be a "
                "DiagnosticSnapshot instance."
            )

        normalized_bundle_id = _normalize_bundle_id(
            bundle_id
        )
        normalized_archive_path = (
            _normalize_archive_path(archive_path)
        )

        try:
            self.database.initialize()
            connection = self.database.connect()
        except RunHistoryDatabaseError as error:
            raise RunHistoryStoreError(
                "Run history database could not be prepared."
            ) from error

        try:
            connection.execute("BEGIN IMMEDIATE")

            run_id = self._insert_monitoring_run(
                connection=connection,
                snapshot=snapshot,
                bundle_id=normalized_bundle_id,
                archive_path=normalized_archive_path,
            )

            self._insert_system_metrics(
                connection,
                run_id,
                snapshot.system_metrics,
            )
            self._insert_network_checks(
                connection,
                run_id,
                snapshot.network_checks,
            )
            self._insert_service_checks(
                connection,
                run_id,
                snapshot.services,
            )
            self._insert_process_checks(
                connection,
                run_id,
                snapshot.processes,
            )
            self._insert_log_checks(
                connection,
                run_id,
                snapshot.logs,
            )
            self._insert_incidents(
                connection,
                run_id,
                snapshot.incidents,
            )

            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            raise RunHistoryStoreError(
                "Diagnostic run could not be saved "
                "to run history."
            ) from error
        finally:
            connection.close()

        return RunHistoryEntry(
            run_id=run_id,
            generated_at=snapshot.generated_at,
            host_name=snapshot.host_name,
            overall_status=snapshot.overall_status,
            system_status=(
                snapshot.system_overall_status
            ),
            network_status=(
                snapshot.network_overall_status
            ),
            service_status=(
                snapshot.service_overall_status
            ),
            process_status=(
                snapshot.process_overall_status
            ),
            log_status=snapshot.log_overall_status,
            active_incident_count=(
                snapshot.active_incident_count
            ),
            resolved_incident_count=(
                snapshot.resolved_incident_count
            ),
            bundle_id=normalized_bundle_id,
            archive_path=normalized_archive_path,
        )

    @staticmethod
    def _insert_monitoring_run(
        *,
        connection: sqlite3.Connection,
        snapshot: DiagnosticSnapshot,
        bundle_id: str,
        archive_path: str,
    ) -> int:
        """Insert the parent monitoring run record."""
        cursor = connection.execute(
            """
            INSERT INTO monitoring_runs (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.generated_at.isoformat(),
                snapshot.host_name,
                snapshot.overall_status.value,
                snapshot.system_overall_status.value,
                snapshot.network_overall_status.value,
                snapshot.service_overall_status.value,
                snapshot.process_overall_status.value,
                snapshot.log_overall_status.value,
                snapshot.active_incident_count,
                snapshot.resolved_incident_count,
                bundle_id,
                archive_path,
            ),
        )

        run_id = cursor.lastrowid

        if run_id is None or run_id <= 0:
            raise sqlite3.IntegrityError(
                "SQLite did not return a valid run ID."
            )

        return run_id

    @staticmethod
    def _insert_system_metrics(
        connection: sqlite3.Connection,
        run_id: int,
        metrics: Iterable[DiagnosticSystemMetric],
    ) -> None:
        """Insert all system metrics."""
        connection.executemany(
            """
            INSERT INTO system_metrics (
                run_id,
                metric_name,
                label,
                value_percent,
                health_status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    metric.metric_name,
                    metric.label,
                    metric.value_percent,
                    metric.health_status.value,
                )
                for metric in metrics
            ),
        )

    @staticmethod
    def _insert_network_checks(
        connection: sqlite3.Connection,
        run_id: int,
        checks: Iterable[DiagnosticNetworkCheck],
    ) -> None:
        """Insert all network check results."""
        connection.executemany(
            """
            INSERT INTO network_checks (
                run_id,
                check_index,
                check_type,
                target,
                check_status,
                health_status,
                latency_ms,
                resolved_address,
                failure_reason,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    check_index,
                    check.check_type.value,
                    check.target,
                    check.check_status.value,
                    check.health_status.value,
                    check.latency_ms,
                    check.resolved_address,
                    _optional_enum_value(
                        check.failure_reason
                    ),
                    check.error_message,
                )
                for check_index, check in enumerate(checks)
            ),
        )

    @staticmethod
    def _insert_service_checks(
        connection: sqlite3.Connection,
        run_id: int,
        services: Iterable[DiagnosticServiceRecord],
    ) -> None:
        """Insert all Linux service results."""
        connection.executemany(
            """
            INSERT INTO service_checks (
                run_id,
                service_name,
                label,
                check_status,
                health_status,
                load_state,
                active_state,
                sub_state,
                failure_reason,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    service.service_name,
                    service.label,
                    service.check_status.value,
                    service.health_status.value,
                    service.load_state,
                    service.active_state,
                    service.sub_state,
                    _optional_enum_value(
                        service.failure_reason
                    ),
                    service.error_message,
                )
                for service in services
            ),
        )

    @staticmethod
    def _insert_process_checks(
        connection: sqlite3.Connection,
        run_id: int,
        processes: Iterable[DiagnosticProcessRecord],
    ) -> None:
        """Insert process summaries and their PIDs."""
        process_records = tuple(processes)

        connection.executemany(
            """
            INSERT INTO process_checks (
                run_id,
                process_name,
                label,
                required,
                check_status,
                health_status,
                instance_count,
                total_cpu_percent,
                total_memory_mb,
                longest_runtime_seconds,
                failure_reason,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    process.process_name,
                    process.label,
                    int(process.required),
                    process.check_status.value,
                    process.health_status.value,
                    process.instance_count,
                    process.total_cpu_percent,
                    process.total_memory_mb,
                    process.longest_runtime_seconds,
                    _optional_enum_value(
                        process.failure_reason
                    ),
                    process.error_message,
                )
                for process in process_records
            ),
        )

        connection.executemany(
            """
            INSERT INTO process_pids (
                run_id,
                process_name,
                pid
            )
            VALUES (?, ?, ?)
            """,
            (
                (
                    run_id,
                    process.process_name,
                    pid,
                )
                for process in process_records
                for pid in process.pids
            ),
        )

    @staticmethod
    def _insert_log_checks(
        connection: sqlite3.Connection,
        run_id: int,
        logs: Iterable[DiagnosticLogRecord],
    ) -> None:
        """Insert all analyzed log results."""
        connection.executemany(
            """
            INSERT INTO log_checks (
                run_id,
                source_id,
                label,
                path,
                required,
                scan_status,
                health_status,
                total_lines_scanned,
                match_count,
                failure_reason,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    log.source_id,
                    log.label,
                    log.path,
                    int(log.required),
                    log.scan_status.value,
                    log.health_status.value,
                    log.total_lines_scanned,
                    log.match_count,
                    _optional_enum_value(
                        log.failure_reason
                    ),
                    log.error_message,
                )
                for log in logs
            ),
        )

    @staticmethod
    def _insert_incidents(
        connection: sqlite3.Connection,
        run_id: int,
        incidents: Iterable[DiagnosticIncidentRecord],
    ) -> None:
        """Insert the incident state observed during the run."""
        connection.executemany(
            """
            INSERT INTO incident_snapshots (
                run_id,
                incident_id,
                source_type,
                source_id,
                source_label,
                severity,
                status,
                description,
                first_seen_at,
                last_seen_at,
                occurrence_count,
                resolved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    run_id,
                    incident.incident_id,
                    incident.source_type.value,
                    incident.source_id,
                    incident.source_label,
                    incident.severity.value,
                    incident.status.value,
                    incident.description,
                    incident.first_seen_at.isoformat(),
                    incident.last_seen_at.isoformat(),
                    incident.occurrence_count,
                    _optional_datetime_value(
                        incident.resolved_at
                    ),
                )
                for incident in incidents
            ),
        )
