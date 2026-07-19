"""Protocols required by the LabOps AI API layer."""
from __future__ import annotations

from typing import Protocol

from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry


class RunHistoryReader(Protocol):
    """Define read-only run history operations."""

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        """Return one run by identifier."""

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        """Return the newest matching run."""

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        """Return recent matching runs."""
