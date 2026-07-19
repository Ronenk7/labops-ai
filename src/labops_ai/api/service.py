"""Application service for read-only run history access."""
from __future__ import annotations

from dataclasses import dataclass

from labops_ai.api.contracts import RunHistoryReader
from labops_ai.api.schemas import RunHistoryResponse
from labops_ai.health_status import HealthStatus


@dataclass(frozen=True, slots=True)
class RunHistoryApiService:
    """Convert persisted history into API response models."""

    reader: RunHistoryReader

    def __post_init__(self) -> None:
        """Validate the injected reader dependency."""
        for method_name in (
            "get_by_id",
            "get_latest",
            "list_recent",
        ):
            if not callable(
                getattr(self.reader, method_name, None)
            ):
                raise TypeError(
                    "reader must provide callable "
                    f"{method_name}."
                )

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryResponse | None:
        """Return one API run response by identifier."""
        entry = self.reader.get_by_id(run_id)

        if entry is None:
            return None

        return RunHistoryResponse.from_entry(entry)

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryResponse | None:
        """Return the newest API run response."""
        entry = self.reader.get_latest(
            host_name=host_name
        )

        if entry is None:
            return None

        return RunHistoryResponse.from_entry(entry)

    def list_recent(
        self,
        *,
        limit: int,
        status: HealthStatus | None,
        host_name: str | None,
    ) -> list[RunHistoryResponse]:
        """Return recent API run responses."""
        entries = self.reader.list_recent(
            limit=limit,
            status=status,
            host_name=host_name,
        )

        return [
            RunHistoryResponse.from_entry(entry)
            for entry in entries
        ]
    def suggest_hosts(
        self,
        *,
        prefix: str,
        limit: int,
    ) -> list[str]:
        """Return matching host suggestions."""
        suggestion_reader = getattr(
            self.reader,
            "suggest_hosts",
            None,
        )

        if not callable(suggestion_reader):
            raise TypeError(
                "reader must provide callable "
                "suggest_hosts."
            )

        return list(
            suggestion_reader(
                prefix=prefix,
                limit=limit,
            )
        )
