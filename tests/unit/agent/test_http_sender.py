"""Tests for HTTP heartbeat delivery."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request

import pytest

from labops_ai.agent import (
    HeartbeatDeliveryError,
    HttpHeartbeatSender,
)
from labops_ai.hosts import HostHeartbeat


pytestmark = pytest.mark.unit

BASE_TIME = datetime(
    2026,
    7,
    20,
    18,
    0,
    tzinfo=timezone.utc,
)


class FakeResponse:
    """Provide a minimal successful HTTP response."""

    status = 200

    def __enter__(self) -> "FakeResponse":
        """Enter the response context."""
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Exit the response context."""


class RecordingOpener:
    """Record HTTP requests or raise an error."""

    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        """Initialize the fake opener."""
        self.error = error
        self.calls: list[
            tuple[Request, float]
        ] = []

    def __call__(
        self,
        request: Request,
        *,
        timeout: float,
    ) -> FakeResponse:
        """Record one outgoing request."""
        self.calls.append(
            (
                request,
                timeout,
            )
        )

        if self.error is not None:
            raise self.error

        return FakeResponse()


def build_heartbeat() -> HostHeartbeat:
    """Create one deterministic heartbeat."""
    return HostHeartbeat(
        host_id="host-001",
        host_name="lab-node-01",
        address="10.0.0.10",
        operating_system="Ubuntu 24.04",
        architecture="x86_64",
        agent_version="0.1.0",
        observed_at=BASE_TIME,
    )


def test_sends_heartbeat_as_json_post() -> None:
    """Send the API contract as a JSON request."""
    opener = RecordingOpener()
    sender = HttpHeartbeatSender(
        opener=opener,
    )
    heartbeat = build_heartbeat()

    sender.send(
        url=(
            "http://127.0.0.1:8000"
            "/api/v1/hosts/heartbeat"
        ),
        heartbeat=heartbeat,
        timeout_seconds=5,
    )

    assert len(opener.calls) == 1

    request, timeout = opener.calls[0]

    assert request.full_url == (
        "http://127.0.0.1:8000"
        "/api/v1/hosts/heartbeat"
    )
    assert request.get_method() == "POST"
    assert timeout == 5.0

    headers = {
        key.lower(): value
        for key, value in request.header_items()
    }

    assert (
        headers["content-type"]
        == "application/json"
    )

    payload = json.loads(
        request.data.decode("utf-8")
    )

    assert payload == {
        "host_id": "host-001",
        "host_name": "lab-node-01",
        "address": "10.0.0.10",
        "operating_system": "Ubuntu 24.04",
        "architecture": "x86_64",
        "agent_version": "0.1.0",
        "observed_at": (
            "2026-07-20T18:00:00+00:00"
        ),
    }


def test_wraps_network_failure() -> None:
    """Convert network errors into delivery errors."""
    sender = HttpHeartbeatSender(
        opener=RecordingOpener(
            error=URLError(
                "Connection refused"
            ),
        ),
    )

    with pytest.raises(
        HeartbeatDeliveryError,
        match="Failed to deliver heartbeat",
    ):
        sender.send(
            url=(
                "http://127.0.0.1:8000"
                "/api/v1/hosts/heartbeat"
            ),
            heartbeat=build_heartbeat(),
            timeout_seconds=5,
        )