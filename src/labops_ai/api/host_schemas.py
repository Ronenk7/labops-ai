"""Validated API contracts for monitored hosts."""
from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from labops_ai.hosts import (
    HostAvailability,
    HostHeartbeat,
    HostStatusSnapshot,
)


class HostHeartbeatRequest(BaseModel):
    """Represent one heartbeat received from a host agent."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    host_id: str = Field(min_length=1, max_length=128)
    host_name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(
        min_length=1,
        max_length=255,
    )
    architecture: str = Field(
        min_length=1,
        max_length=128,
    )
    agent_version: str = Field(
        min_length=1,
        max_length=64,
    )
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware heartbeat timestamp."""
        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "observed_at must be timezone-aware."
            )

        return value

    def to_domain(self) -> HostHeartbeat:
        """Convert the API request into a domain heartbeat."""
        return HostHeartbeat(
            host_id=self.host_id,
            host_name=self.host_name,
            address=self.address,
            operating_system=self.operating_system,
            architecture=self.architecture,
            agent_version=self.agent_version,
            observed_at=self.observed_at,
        )


class HostResponse(BaseModel):
    """Represent one host with calculated availability."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    host_id: str
    host_name: str
    address: str
    operating_system: str
    architecture: str
    agent_version: str

    registered_at: datetime
    last_seen_at: datetime
    evaluated_at: datetime

    availability: HostAvailability
    heartbeat_age_seconds: float = Field(ge=0)

    @classmethod
    def from_snapshot(
        cls,
        snapshot: HostStatusSnapshot,
    ) -> "HostResponse":
        """Convert one domain status snapshot."""
        if not isinstance(
            snapshot,
            HostStatusSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HostStatusSnapshot."
            )

        host = snapshot.host

        return cls(
            host_id=host.host_id,
            host_name=host.host_name,
            address=host.address,
            operating_system=host.operating_system,
            architecture=host.architecture,
            agent_version=host.agent_version,
            registered_at=host.registered_at,
            last_seen_at=host.last_seen_at,
            evaluated_at=snapshot.evaluated_at,
            availability=snapshot.availability,
            heartbeat_age_seconds=(
                snapshot.heartbeat_age_seconds
            ),
        )
