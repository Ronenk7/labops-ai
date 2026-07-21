"""Central ingestion service for remote monitoring runs."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from labops_ai.diagnostics import (
    DiagnosticBundleWriteResult,
    DiagnosticSnapshot,
    parse_diagnostic_payload,
)
from labops_ai.history import (
    RunHistoryEntry,
    RunHistoryStoreError,
)


SnapshotParser = Callable[
    [Mapping[str, Any]],
    DiagnosticSnapshot,
]


class DiagnosticWriterProtocol(Protocol):
    """Define diagnostic bundle persistence."""

    def write(
        self,
        snapshot: DiagnosticSnapshot,
    ) -> DiagnosticBundleWriteResult:
        """Write one central diagnostic archive."""
        ...


class RunHistoryWriterProtocol(Protocol):
    """Define complete run-history persistence."""

    def save(
        self,
        snapshot: DiagnosticSnapshot,
        *,
        bundle_id: str,
        archive_path: str | Path,
    ) -> RunHistoryEntry:
        """Save one complete monitoring run."""
        ...


@dataclass(frozen=True, slots=True)
class RunIngestionService:
    """Validate and persist one remote monitoring run."""

    bundle_writer: DiagnosticWriterProtocol
    history_store: RunHistoryWriterProtocol
    snapshot_parser: SnapshotParser = (
        parse_diagnostic_payload
    )

    def __post_init__(self) -> None:
        """Validate all ingestion dependencies."""
        if not callable(
            getattr(
                self.bundle_writer,
                "write",
                None,
            )
        ):
            raise TypeError(
                "bundle_writer must provide "
                "a callable write method."
            )

        if not callable(
            getattr(
                self.history_store,
                "save",
                None,
            )
        ):
            raise TypeError(
                "history_store must provide "
                "a callable save method."
            )

        if not callable(self.snapshot_parser):
            raise TypeError(
                "snapshot_parser must be callable."
            )

    def ingest(
        self,
        diagnostics: Mapping[str, Any],
    ) -> RunHistoryEntry:
        """Store one validated remote run centrally."""
        snapshot = self.snapshot_parser(diagnostics)
        bundle = self.bundle_writer.write(snapshot)

        try:
            return self.history_store.save(
                snapshot,
                bundle_id=bundle.bundle_id,
                archive_path=bundle.archive_path,
            )
        except RunHistoryStoreError:
            self._remove_orphaned_archive(
                bundle.archive_path
            )
            raise

    @staticmethod
    def _remove_orphaned_archive(
        archive_path: str | Path,
    ) -> None:
        """Remove a ZIP when SQLite persistence fails."""
        try:
            Path(archive_path).unlink(
                missing_ok=True
            )
        except OSError:
            pass
