"""HTTP delivery for remote host heartbeats."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from labops_ai.agent.agent import (
    HeartbeatDeliveryError,
)
from labops_ai.hosts import HostHeartbeat


HttpOpener = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class HttpHeartbeatSender:
    """Send host heartbeats to the central HTTP API."""

    opener: HttpOpener = urlopen

    def __post_init__(self) -> None:
        """Validate the HTTP dependency."""
        if not callable(self.opener):
            raise TypeError(
                "opener must be callable."
            )

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        """Send one heartbeat as a JSON POST request."""
        if not isinstance(url, str):
            raise TypeError(
                "url must be a string."
            )

        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError(
                "url must not be empty."
            )

        if not isinstance(
            heartbeat,
            HostHeartbeat,
        ):
            raise TypeError(
                "heartbeat must be a HostHeartbeat."
            )

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(
                timeout_seconds,
                (int, float),
            )
        ):
            raise TypeError(
                "timeout_seconds must be numeric."
            )

        normalized_timeout = float(
            timeout_seconds
        )

        if normalized_timeout <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        payload = {
            "host_id": heartbeat.host_id,
            "host_name": heartbeat.host_name,
            "address": heartbeat.address,
            "operating_system": (
                heartbeat.operating_system
            ),
            "architecture": heartbeat.architecture,
            "agent_version": heartbeat.agent_version,
            "observed_at": (
                heartbeat.observed_at.isoformat()
            ),
        }

        request = Request(
            url=normalized_url,
            data=json.dumps(
                payload,
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with self.opener(
                request,
                timeout=normalized_timeout,
            ) as response:
                status_code = getattr(
                    response,
                    "status",
                    200,
                )

        except (
            URLError,
            TimeoutError,
            OSError,
        ) as error:
            raise HeartbeatDeliveryError(
                "Failed to deliver heartbeat "
                f"to {normalized_url}."
            ) from error

        if not (
            200
            <= status_code
            < 300
        ):
            raise HeartbeatDeliveryError(
                "Failed to deliver heartbeat: "
                f"server returned HTTP {status_code}."
            )