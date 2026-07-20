"""Application service for the central host registry."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from labops_ai.hosts.models import (
    HostAvailability,
    HostHeartbeat,
    HostRecord,
)
from labops_ai.hosts.status import (
    HostStatusEvaluator,
)


Clock = Callable[[], datetime]


class HostRegistryProtocol(Protocol):
    """Define storage operations required by the service."""

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Create or update a host record."""
        ...

    def get_by_id(
        self,
        host_id: str,
    ) -> HostRecord | None:
        """Return one host by identifier."""
        ...

    def list_all(self) -> tuple[HostRecord, ...]:
        """Return all registered hosts."""
        ...


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _validate_timestamp(
    value: object,
    field_name: str,
) -> datetime:
    """Require one timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime."
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be timezone-aware."
        )

    return value


@dataclass(frozen=True, slots=True)
class HostStatusSnapshot:
    """Represent one host and its calculated availability."""

    host: HostRecord
    availability: HostAvailability
    evaluated_at: datetime
    heartbeat_age_seconds: float

    def __post_init__(self) -> None:
        """Validate the complete calculated snapshot."""
        if not isinstance(self.host, HostRecord):
            raise TypeError(
                "host must be a HostRecord."
            )

        if not isinstance(
            self.availability,
            HostAvailability,
        ):
            raise TypeError(
                "availability must be a "
                "HostAvailability."
            )

        evaluated_at = _validate_timestamp(
            self.evaluated_at,
            "evaluated_at",
        )

        if evaluated_at < self.host.last_seen_at:
            raise ValueError(
                "evaluated_at must not be earlier "
                "than host.last_seen_at."
            )

        if (
            isinstance(
                self.heartbeat_age_seconds,
                bool,
            )
            or not isinstance(
                self.heartbeat_age_seconds,
                (int, float),
            )
        ):
            raise TypeError(
                "heartbeat_age_seconds must be numeric."
            )

        if self.heartbeat_age_seconds < 0:
            raise ValueError(
                "heartbeat_age_seconds must not "
                "be negative."
            )


@dataclass(frozen=True, slots=True)
class HostRegistryService:
    """Coordinate host persistence and availability."""

    registry: HostRegistryProtocol
    evaluator: HostStatusEvaluator
    clock: Clock = utc_now

    def __post_init__(self) -> None:
        """Validate service dependencies."""
        for method_name in (
            "record_heartbeat",
            "get_by_id",
            "list_all",
        ):
            method = getattr(
                self.registry,
                method_name,
                None,
            )

            if not callable(method):
                raise TypeError(
                    "registry must provide a callable "
                    f"{method_name} method."
                )

        if not isinstance(
            self.evaluator,
            HostStatusEvaluator,
        ):
            raise TypeError(
                "evaluator must be a "
                "HostStatusEvaluator."
            )

        if not callable(self.clock):
            raise TypeError(
                "clock must be callable."
            )

    def record_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostStatusSnapshot:
        """Store a heartbeat and return current host status."""
        if not isinstance(heartbeat, HostHeartbeat):
            raise TypeError(
                "heartbeat must be a HostHeartbeat."
            )

        host = self.registry.record_heartbeat(
            heartbeat
        )

        return self._build_snapshot(
            host,
            evaluated_at=heartbeat.observed_at,
        )

    def get_by_id(
        self,
        host_id: str,
        *,
        evaluated_at: datetime | None = None,
    ) -> HostStatusSnapshot | None:
        """Return one host with calculated availability."""
        host = self.registry.get_by_id(host_id)

        if host is None:
            return None

        return self._build_snapshot(
            host,
            evaluated_at=self._resolve_time(
                evaluated_at
            ),
        )

    def list_all(
        self,
        *,
        evaluated_at: datetime | None = None,
    ) -> tuple[HostStatusSnapshot, ...]:
        """Return all hosts with calculated availability."""
        resolved_time = self._resolve_time(
            evaluated_at
        )

        return tuple(
            self._build_snapshot(
                host,
                evaluated_at=resolved_time,
            )
            for host in self.registry.list_all()
        )

    def _resolve_time(
        self,
        evaluated_at: datetime | None,
    ) -> datetime:
        """Resolve an explicit time or the service clock."""
        resolved = (
            self.clock()
            if evaluated_at is None
            else evaluated_at
        )

        return _validate_timestamp(
            resolved,
            "evaluated_at",
        )

    def _build_snapshot(
        self,
        host: HostRecord,
        *,
        evaluated_at: datetime,
    ) -> HostStatusSnapshot:
        """Calculate one complete host-status snapshot."""
        availability = self.evaluator.evaluate(
            host,
            evaluated_at=evaluated_at,
        )

        heartbeat_age_seconds = (
            evaluated_at - host.last_seen_at
        ).total_seconds()

        return HostStatusSnapshot(
            host=host,
            availability=availability,
            evaluated_at=evaluated_at,
            heartbeat_age_seconds=(
                heartbeat_age_seconds
            ),
        )
