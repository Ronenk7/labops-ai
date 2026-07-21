"""Tests for full monitoring Agent delivery."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import pytest

from labops_ai.agent import (
    HostAgent,
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
    HttpMonitoringRunSender,
    MonitoringRunDeliveryError,
    run_agent_forever,
)
from labops_ai.diagnostics import (
    DiagnosticSnapshot,
    parse_diagnostic_payload,
)
from labops_ai.hosts import HostHeartbeat
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit


def build_snapshot() -> DiagnosticSnapshot:
    """Build a valid remote diagnostic snapshot."""
    payload = deepcopy(
        load_test_fixture(
            "diagnostics/remote_run_payload.json"
        )
    )

    return parse_diagnostic_payload(payload)


def build_config(
    *,
    heartbeat_interval: float = 15.0,
    monitoring_interval: float = 60.0,
    max_attempts: int = 3,
) -> HostAgentConfig:
    """Build one deterministic Agent configuration."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(),
        server=HostAgentServerConfig(
            base_url="http://127.0.0.1:8000",
            heartbeat_path=(
                "/api/v1/hosts/heartbeat"
            ),
            run_ingestion_path=(
                "/api/v1/runs/ingest"
            ),
            request_timeout_seconds=5.0,
        ),
        schedule=HostAgentScheduleConfig(
            interval_seconds=heartbeat_interval,
            monitoring_interval_seconds=(
                monitoring_interval
            ),
        ),
        retry=HostAgentRetryConfig(
            max_attempts=max_attempts,
            initial_backoff_seconds=1.0,
            max_backoff_seconds=5.0,
        ),
    )


class RecordingHeartbeatSender:
    """Record heartbeat deliveries."""

    def __init__(self) -> None:
        self.calls: list[HostHeartbeat] = []

    def send(
        self,
        *,
        url: str,
        heartbeat: HostHeartbeat,
        timeout_seconds: float,
    ) -> None:
        self.calls.append(heartbeat)


class ControlledMonitoringSender:
    """Record and optionally fail run deliveries."""

    def __init__(
        self,
        failures_before_success: int = 0,
    ) -> None:
        self.failures_before_success = (
            failures_before_success
        )
        self.attempts = 0
        self.calls: list[
            DiagnosticSnapshot
        ] = []

    def send(
        self,
        *,
        url: str,
        snapshot: DiagnosticSnapshot,
        timeout_seconds: float,
    ) -> None:
        self.attempts += 1

        if (
            self.attempts
            <= self.failures_before_success
        ):
            raise MonitoringRunDeliveryError(
                "Temporary ingestion failure."
            )

        self.calls.append(snapshot)


def build_agent(
    *,
    config: HostAgentConfig | None = None,
    monitoring_sender: (
        ControlledMonitoringSender | None
    ) = None,
    sleeper=lambda seconds: None,
) -> tuple[
    HostAgent,
    RecordingHeartbeatSender,
    ControlledMonitoringSender,
]:
    """Build a full deterministic Agent."""
    heartbeat_sender = (
        RecordingHeartbeatSender()
    )
    resolved_monitoring_sender = (
        monitoring_sender
        if monitoring_sender is not None
        else ControlledMonitoringSender()
    )
    snapshot = build_snapshot()

    agent = HostAgent(
        config=(
            config
            if config is not None
            else build_config()
        ),
        sender=heartbeat_sender,
        clock=lambda: datetime(
            2026,
            7,
            21,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        host_name_provider=(
            lambda: "lab-node-02"
        ),
        address_provider=lambda: "172.18.0.2",
        operating_system_provider=(
            lambda: "Debian GNU/Linux 12"
        ),
        architecture_provider=lambda: "x86_64",
        agent_version="0.1.0",
        sleeper=sleeper,
        monitoring_executor=lambda: snapshot,
        monitoring_sender=(
            resolved_monitoring_sender
        ),
    )

    return (
        agent,
        heartbeat_sender,
        resolved_monitoring_sender,
    )


class FakeResponse:
    """Provide one successful HTTP response."""

    status = 201

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        traceback,
    ) -> None:
        return None


class RecordingOpener:
    """Record one urllib request."""

    def __init__(self) -> None:
        self.request = None
        self.timeout = None

    def __call__(
        self,
        request,
        *,
        timeout: float,
    ) -> FakeResponse:
        self.request = request
        self.timeout = timeout
        return FakeResponse()


def test_http_sender_posts_complete_diagnostics() -> None:
    """Send the central ingestion request contract."""
    opener = RecordingOpener()
    sender = HttpMonitoringRunSender(
        opener=opener
    )
    snapshot = build_snapshot()

    sender.send(
        url=(
            "http://127.0.0.1:8000"
            "/api/v1/runs/ingest"
        ),
        snapshot=snapshot,
        timeout_seconds=10.0,
    )

    assert opener.request is not None
    assert opener.request.full_url.endswith(
        "/api/v1/runs/ingest"
    )
    assert opener.request.get_method() == "POST"
    assert opener.timeout == 10.0

    body: dict[str, Any] = json.loads(
        opener.request.data.decode("utf-8")
    )

    assert body["diagnostics"]["host_name"] == (
        "lab-node-02"
    )
    assert body["diagnostics"][
        "schema_version"
    ] == 1


def test_agent_retries_monitoring_delivery() -> None:
    """Use the configured retry policy for runs."""
    sender = ControlledMonitoringSender(
        failures_before_success=1
    )
    sleep_calls: list[float] = []

    agent, _, _ = build_agent(
        config=build_config(
            max_attempts=2
        ),
        monitoring_sender=sender,
        sleeper=sleep_calls.append,
    )

    snapshot = agent.run_monitoring_once()

    assert snapshot.host_name == "lab-node-02"
    assert sender.attempts == 2
    assert len(sender.calls) == 1
    assert sleep_calls == [1.0]


def test_scheduler_uses_independent_intervals() -> None:
    """Schedule heartbeats more often than full runs."""
    agent, heartbeat_sender, run_sender = (
        build_agent(
            config=build_config(
                heartbeat_interval=5.0,
                monitoring_interval=12.0,
            )
        )
    )

    class FakeClock:
        def __init__(self) -> None:
            self.value = 0.0

        def __call__(self) -> float:
            return self.value

        def sleep(self, seconds: float) -> None:
            self.value += seconds

    clock = FakeClock()

    run_agent_forever(
        agent,
        sleeper=clock.sleep,
        should_stop=lambda: clock.value >= 26,
        monotonic=clock,
    )

    assert len(heartbeat_sender.calls) == 6
    assert len(run_sender.calls) == 3
