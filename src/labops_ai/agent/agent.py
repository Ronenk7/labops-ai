"""Remote host-agent application service."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from labops_ai.agent.config import HostAgentConfig
from labops_ai.hosts import HostHeartbeat


Clock = Callable[[], datetime]
TextProvider = Callable[[], str]
Sleeper = Callable[[float], None]


class HeartbeatDeliveryError(RuntimeError):
    """Represent a failed heartbeat delivery."""


class HeartbeatSender(Protocol):
    """Define heartbeat delivery operations."""

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Send one heartbeat to the central API."""
        ...


def _validate_text(
    value: object,
    field_name: str,
) -> str:
    """Validate and normalize required text."""
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class HostAgent:
    """Collect and send remote host heartbeats."""

    config: HostAgentConfig
    sender: HeartbeatSender
    clock: Clock
    host_name_provider: TextProvider
    address_provider: TextProvider
    operating_system_provider: TextProvider
    architecture_provider: TextProvider
    agent_version: str
    sleeper: Sleeper = time.sleep

    def __post_init__(self) -> None:
        """Validate agent dependencies."""
        if not isinstance(
            self.config,
            HostAgentConfig,
        ):
            raise TypeError(
                "config must be a HostAgentConfig."
            )

        send_method = getattr(
            self.sender,
            "send",
            None,
        )

        if not callable(send_method):
            raise TypeError(
                "sender must provide a callable "
                "send method."
            )

        callables = (
            ("clock", self.clock),
            (
                "host_name_provider",
                self.host_name_provider,
            ),
            (
                "address_provider",
                self.address_provider,
            ),
            (
                "operating_system_provider",
                self.operating_system_provider,
            ),
            (
                "architecture_provider",
                self.architecture_provider,
            ),
            ("sleeper", self.sleeper),
        )

        for callable_name, callable_value in callables:
            if not callable(callable_value):
                raise TypeError(
                    f"{callable_name} must be callable."
                )

        object.__setattr__(
            self,
            "agent_version",
            _validate_text(
                self.agent_version,
                "agent_version",
            ),
        )

    def run_once(self) -> HostHeartbeat:
        """Build and send one host heartbeat."""
        heartbeat = self._build_heartbeat()

        self._send_with_retry(heartbeat)

        return heartbeat

    def _build_heartbeat(self) -> HostHeartbeat:
        """Collect local metadata into one heartbeat."""
        host_name = self.host_name_provider()

        host_id = (
            self.config.identity.host_id_override
            or host_name
        )

        return HostHeartbeat(
            host_id=host_id,
            host_name=host_name,
            address=self.address_provider(),
            operating_system=(
                self.operating_system_provider()
            ),
            architecture=(
                self.architecture_provider()
            ),
            agent_version=self.agent_version,
            observed_at=self.clock(),
        )

    def _send_with_retry(
        self,
        heartbeat: HostHeartbeat,
    ) -> None:
        """Send a heartbeat using bounded retries."""
        retry_config = self.config.retry
        backoff_seconds = (
            retry_config.initial_backoff_seconds
        )

        for attempt in range(
            1,
            retry_config.max_attempts + 1,
        ):
            try:
                self.sender.send(
                    url=(
                        self.config.server
                        .heartbeat_url
                    ),
                    heartbeat=heartbeat,
                    timeout_seconds=(
                        self.config.server
                        .request_timeout_seconds
                    ),
                )
                return

            except HeartbeatDeliveryError:
                if attempt >= retry_config.max_attempts:
                    raise

                self.sleeper(backoff_seconds)

                backoff_seconds = min(
                    backoff_seconds * 2,
                    retry_config.max_backoff_seconds,
                )