"""Evaluate the availability of registered hosts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from labops_ai.hosts.models import (
    HostAvailability,
    HostRecord,
)


@dataclass(frozen=True, slots=True)
class HostAvailabilityPolicy:
    """Define host heartbeat availability thresholds."""

    stale_after_seconds: int
    offline_after_seconds: int

    def __post_init__(self) -> None:
        """Validate availability thresholds."""
        for field_name in (
            "stale_after_seconds",
            "offline_after_seconds",
        ):
            value = getattr(self, field_name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{field_name} must be an integer."
                )

            if value <= 0:
                raise ValueError(
                    f"{field_name} must be positive."
                )

        if (
            self.offline_after_seconds
            <= self.stale_after_seconds
        ):
            raise ValueError(
                "offline_after_seconds must be greater "
                "than stale_after_seconds."
            )


class HostStatusEvaluator:
    """Calculate host availability from its last heartbeat."""

    def __init__(
        self,
        policy: HostAvailabilityPolicy,
    ) -> None:
        """Initialize the evaluator."""
        if not isinstance(
            policy,
            HostAvailabilityPolicy,
        ):
            raise TypeError(
                "policy must be a "
                "HostAvailabilityPolicy."
            )

        self._policy = policy

    def evaluate(
        self,
        host: HostRecord,
        *,
        evaluated_at: datetime,
    ) -> HostAvailability:
        """Return the host availability at a specific time."""
        if not isinstance(host, HostRecord):
            raise TypeError(
                "host must be a HostRecord."
            )

        if not isinstance(evaluated_at, datetime):
            raise TypeError(
                "evaluated_at must be a datetime."
            )

        if (
            evaluated_at.tzinfo is None
            or evaluated_at.utcoffset() is None
        ):
            raise ValueError(
                "evaluated_at must be timezone-aware."
            )

        if evaluated_at < host.last_seen_at:
            raise ValueError(
                "evaluated_at must not be earlier "
                "than host.last_seen_at."
            )

        age_seconds = (
            evaluated_at - host.last_seen_at
        ).total_seconds()

        if (
            age_seconds
            < self._policy.stale_after_seconds
        ):
            return HostAvailability.ONLINE

        if (
            age_seconds
            < self._policy.offline_after_seconds
        ):
            return HostAvailability.STALE

        return HostAvailability.OFFLINE
