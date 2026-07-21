"""Unit tests for HTTP heartbeat delivery."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.error import URLError
from urllib.request import Request

import pytest

from labops_ai.agent import (
    HeartbeatDeliveryError,
    HttpHeartbeatSender,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/http_sender_cases.json"
)
HEARTBEAT_CASE = CASES["heartbeat"]
REQUEST_CASE = CASES["request"]

ERROR_TYPES: dict[
    str,
    type[Exception],
] = {
    "TypeError": TypeError,
    "ValueError": ValueError,
}


class FakeResponse:
    """Provide a minimal HTTP response."""

    def __init__(
        self,
        status: int,
    ) -> None:
        """Store the simulated HTTP status."""
        self.status = status

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
    """Record requests or simulate transport failure."""

    def __init__(
        self,
        *,
        response_status: int = 200,
        error: Exception | None = None,
    ) -> None:
        """Initialize deterministic HTTP behavior."""
        self.response_status = response_status
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
        """Record one outgoing HTTP request."""
        self.calls.append(
            (
                request,
                timeout,
            )
        )

        if self.error is not None:
            raise self.error

        return FakeResponse(
            self.response_status
        )


def build_heartbeat() -> HostHeartbeat:
    """Build heartbeat data from the fixture."""
    return HostHeartbeat(
        host_id=HEARTBEAT_CASE["host_id"],
        host_name=HEARTBEAT_CASE["host_name"],
        address=HEARTBEAT_CASE["address"],
        operating_system=(
            HEARTBEAT_CASE["operating_system"]
        ),
        architecture=(
            HEARTBEAT_CASE["architecture"]
        ),
        agent_version=(
            HEARTBEAT_CASE["agent_version"]
        ),
        observed_at=datetime.fromisoformat(
            HEARTBEAT_CASE["observed_at"]
        ),
    )


def build_network_error(
    case: dict[str, Any],
) -> Exception:
    """Build the configured simulated network error."""
    error_kind = case["error_kind"]
    message = case["message"]

    if error_kind == "url_error":
        return URLError(message)

    if error_kind == "timeout":
        return TimeoutError(message)

    if error_kind == "os_error":
        return OSError(message)

    raise ValueError(
        f"Unsupported error kind: {error_kind}"
    )


def test_sends_heartbeat_as_json_post() -> None:
    """Send the API contract as a JSON POST."""
    opener = RecordingOpener()
    sender = HttpHeartbeatSender(
        opener=opener,
    )

    sender.send(
        url=REQUEST_CASE["url"],
        heartbeat=build_heartbeat(),
        timeout_seconds=(
            REQUEST_CASE["timeout_seconds"]
        ),
    )

    assert len(opener.calls) == 1

    request, timeout = opener.calls[0]

    assert request.full_url == (
        REQUEST_CASE["expected_url"]
    )
    assert request.get_method() == "POST"
    assert timeout == (
        REQUEST_CASE[
            "expected_timeout_seconds"
        ]
    )

    headers = {
        key.lower(): value
        for key, value in request.header_items()
    }

    assert headers["content-type"] == (
        "application/json"
    )

    payload = json.loads(
        request.data.decode("utf-8")
    )

    assert payload == (
        REQUEST_CASE["expected_payload"]
    )


@pytest.mark.parametrize(
    "status_code",
    CASES["successful_status_codes"],
)
def test_accepts_every_success_status(
    status_code: int,
) -> None:
    """Accept every HTTP status in the 2xx range."""
    opener = RecordingOpener(
        response_status=status_code,
    )

    HttpHeartbeatSender(
        opener=opener
    ).send(
        url=REQUEST_CASE["expected_url"],
        heartbeat=build_heartbeat(),
        timeout_seconds=5,
    )

    assert len(opener.calls) == 1


@pytest.mark.parametrize(
    "case",
    CASES["network_failures"],
    ids=lambda case: case["id"],
)
def test_wraps_network_failures(
    case: dict[str, Any],
) -> None:
    """Convert transport errors into delivery errors."""
    opener = RecordingOpener(
        error=build_network_error(case),
    )
    sender = HttpHeartbeatSender(
        opener=opener,
    )

    with pytest.raises(
        HeartbeatDeliveryError,
        match="Failed to deliver heartbeat",
    ):
        sender.send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=build_heartbeat(),
            timeout_seconds=5,
        )

    assert len(opener.calls) == 1


@pytest.mark.parametrize(
    "case",
    CASES["http_failure_status_codes"],
    ids=lambda case: case["id"],
)
def test_rejects_http_failure_status(
    case: dict[str, Any],
) -> None:
    """Reject HTTP responses outside the 2xx range."""
    opener = RecordingOpener(
        response_status=case["status_code"],
    )

    with pytest.raises(
        HeartbeatDeliveryError,
        match=f'HTTP {case["status_code"]}',
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=build_heartbeat(),
            timeout_seconds=5,
        )


@pytest.mark.parametrize(
    "case",
    CASES["invalid_urls"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_url(
    case: dict[str, Any],
) -> None:
    """Require a non-empty string URL."""
    opener = RecordingOpener()
    error_type = ERROR_TYPES[
        case["error_type"]
    ]

    with pytest.raises(
        error_type,
        match=case["match"],
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=case["value"],
            heartbeat=build_heartbeat(),
            timeout_seconds=5,
        )

    assert opener.calls == []


@pytest.mark.parametrize(
    "case",
    CASES["invalid_timeout_types"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_timeout_type(
    case: dict[str, Any],
) -> None:
    """Require numeric timeout values."""
    opener = RecordingOpener()

    with pytest.raises(
        TypeError,
        match="timeout_seconds must be numeric",
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=build_heartbeat(),
            timeout_seconds=case["value"],
        )

    assert opener.calls == []


@pytest.mark.parametrize(
    "case",
    CASES["non_positive_timeouts"],
    ids=lambda case: case["id"],
)
def test_rejects_non_positive_timeout(
    case: dict[str, Any],
) -> None:
    """Require a timeout greater than zero."""
    opener = RecordingOpener()

    with pytest.raises(
        ValueError,
        match="timeout_seconds must be positive",
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=build_heartbeat(),
            timeout_seconds=case["value"],
        )

    assert opener.calls == []


@pytest.mark.parametrize(
    "case",
    CASES["non_finite_timeouts"],
    ids=lambda case: case["id"],
)
def test_rejects_non_finite_timeout(
    case: dict[str, Any],
) -> None:
    """Reject NaN and infinite timeout values."""
    opener = RecordingOpener()

    with pytest.raises(
        ValueError,
        match="timeout_seconds must be finite",
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=build_heartbeat(),
            timeout_seconds=float(
                case["value"]
            ),
        )

    assert opener.calls == []


def test_rejects_invalid_heartbeat() -> None:
    """Require the HostHeartbeat API contract."""
    opener = RecordingOpener()

    with pytest.raises(
        TypeError,
        match="heartbeat must be a HostHeartbeat",
    ):
        HttpHeartbeatSender(
            opener=opener
        ).send(
            url=REQUEST_CASE["expected_url"],
            heartbeat=object(),
            timeout_seconds=5,
        )

    assert opener.calls == []


def test_rejects_non_callable_opener() -> None:
    """Require an invokable HTTP dependency."""
    with pytest.raises(
        TypeError,
        match="opener must be callable",
    ):
        HttpHeartbeatSender(
            opener="invalid-opener"
        )
