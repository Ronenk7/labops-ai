"""Domain models for monitored Linux hosts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class HostAvailability(StrEnum):
    """Represent the calculated availability of a host."""

    ONLINE = "ONLINE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"


def _validate_text(
    value: object,
    field_name: str,
) -> str:
    """Validate and normalize one required text field."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return normalized


def _validate_timestamp(
    value: object,
    field_name: str,
) -> datetime:
    """Require a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime."
        )

    if value.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware."
        )

    return value


@dataclass(frozen=True, slots=True)
class HostHeartbeat:
    """Represent one status message sent by a host agent."""

    host_id: str
    host_name: str
    address: str
    operating_system: str
    architecture: str
    agent_version: str
    observed_at: datetime

    def __post_init__(self) -> None:
        """Validate and normalize heartbeat data."""
        for field_name in (
            "host_id",
            "host_name",
            "address",
            "operating_system",
            "architecture",
            "agent_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_text(
                    getattr(self, field_name),
                    field_name,
                ),
            )

        _validate_timestamp(
            self.observed_at,
            "observed_at",
        )


@dataclass(frozen=True, slots=True)
class HostRecord:
    """Represent one host stored in the central registry."""

    host_id: str
    host_name: str
    address: str
    operating_system: str
    architecture: str
    agent_version: str
    registered_at: datetime
    last_seen_at: datetime

    def __post_init__(self) -> None:
        """Validate and normalize the stored host."""
        for field_name in (
            "host_id",
            "host_name",
            "address",
            "operating_system",
            "architecture",
            "agent_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_text(
                    getattr(self, field_name),
                    field_name,
                ),
            )

        registered_at = _validate_timestamp(
            self.registered_at,
            "registered_at",
        )
        last_seen_at = _validate_timestamp(
            self.last_seen_at,
            "last_seen_at",
        )

        if last_seen_at < registered_at:
            raise ValueError(
                "last_seen_at must not be earlier "
                "than registered_at."
            )

    @classmethod
    def register(
        cls,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Create a new registry record from a heartbeat."""
        if not isinstance(heartbeat, HostHeartbeat):
            raise TypeError(
                "heartbeat must be a HostHeartbeat."
            )

        return cls(
            host_id=heartbeat.host_id,
            host_name=heartbeat.host_name,
            address=heartbeat.address,
            operating_system=(
                heartbeat.operating_system
            ),
            architecture=heartbeat.architecture,
            agent_version=heartbeat.agent_version,
            registered_at=heartbeat.observed_at,
            last_seen_at=heartbeat.observed_at,
        )

    def apply_heartbeat(
        self,
        heartbeat: HostHeartbeat,
    ) -> HostRecord:
        """Return an updated record from a newer heartbeat."""
        if not isinstance(heartbeat, HostHeartbeat):
            raise TypeError(
                "heartbeat must be a HostHeartbeat."
            )

        if heartbeat.host_id != self.host_id:
            raise ValueError(
                "Heartbeat host_id does not match "
                "the registered host."
            )

        if heartbeat.observed_at < self.last_seen_at:
            raise ValueError(
                "Heartbeat is older than the current "
                "last_seen_at value."
            )

        return replace(
            self,
            host_name=heartbeat.host_name,
            address=heartbeat.address,
            operating_system=(
                heartbeat.operating_system
            ),
            architecture=heartbeat.architecture,
            agent_version=heartbeat.agent_version,
            last_seen_at=heartbeat.observed_at,
        )
