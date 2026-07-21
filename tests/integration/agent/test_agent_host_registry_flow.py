"""Integration tests for Agent-to-registry heartbeat flow."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from labops_ai.agent import (
    HostAgent,
    HostAgentConfig,
    HostAgentIdentityConfig,
    HostAgentRetryConfig,
    HostAgentScheduleConfig,
    HostAgentServerConfig,
    HttpHeartbeatSender,
)
from labops_ai.api.host_routes import (
    build_host_router,
)
from labops_ai.hosts import (
    HostAvailabilityPolicy,
    HostRegistryService,
    HostStatusEvaluator,
    SqliteHostRegistry,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.integration

AGENT_CASES = load_test_fixture(
    "agent/host_agent_cases.json"
)
INTEGRATION_CASES = load_test_fixture(
    "agent/agent_host_registry_integration_cases.json"
)

BASE_CONFIGURATION = AGENT_CASES[
    "base_configuration"
]
REGISTRY_CASE = INTEGRATION_CASES["registry"]
EXPECTED = INTEGRATION_CASES["expected"]

Clock = Callable[[], datetime]


class ResponseAdapter:
    """Expose the response contract expected by urllib."""

    def __init__(
        self,
        status: int,
    ) -> None:
        """Store the simulated HTTP response status."""
        self.status = status

    def __enter__(
        self,
    ) -> "ResponseAdapter":
        """Enter the HTTP response context."""
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Exit the HTTP response context."""

class FastApiClientOpener:
    """Route urllib requests through FastAPI TestClient."""

    def __init__(
        self,
        client: TestClient,
    ) -> None:
        """Store the isolated FastAPI client."""
        self.client = client
        self.calls: list[
            tuple[str, str, float, int]
        ] = []

    def __call__(
        self,
        request: Request,
        *,
        timeout: float,
    ) -> ResponseAdapter:
        """Send one urllib request into the ASGI app."""
        parsed_url = urlsplit(
            request.full_url
        )

        target = parsed_url.path

        if parsed_url.query:
            target = (
                f"{target}?{parsed_url.query}"
            )

        response = self.client.request(
            method=request.get_method(),
            url=target,
            content=request.data,
            headers=dict(
                request.header_items()
            ),
        )

        self.calls.append(
            (
                request.get_method(),
                request.full_url,
                timeout,
                response.status_code,
            )
        )

        return ResponseAdapter(
            response.status_code
        )


def parse_timestamp(
    value: str,
) -> datetime:
    """Parse an API timestamp including UTC Z notation."""
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def build_agent_config(
    *,
    host_id_override: str,
) -> HostAgentConfig:
    """Build Agent configuration from fixture data."""
    return HostAgentConfig(
        identity=HostAgentIdentityConfig(
            host_id_override=host_id_override,
        ),
        server=HostAgentServerConfig(
            **BASE_CONFIGURATION["server"]
        ),
        schedule=HostAgentScheduleConfig(
            **BASE_CONFIGURATION["schedule"]
        ),
        retry=HostAgentRetryConfig(
            **BASE_CONFIGURATION["retry"]
        ),
    )


def build_application(
    database_path: Path,
    *,
    clock: Clock,
) -> FastAPI:
    """Build isolated host routes backed by SQLite."""
    registry = SqliteHostRegistry(
        database_path=database_path,
        busy_timeout_seconds=(
            REGISTRY_CASE[
                "busy_timeout_seconds"
            ]
        ),
    )

    evaluator = HostStatusEvaluator(
        policy=HostAvailabilityPolicy(
            stale_after_seconds=(
                REGISTRY_CASE[
                    "stale_after_seconds"
                ]
            ),
            offline_after_seconds=(
                REGISTRY_CASE[
                    "offline_after_seconds"
                ]
            ),
        )
    )

    service = HostRegistryService(
        registry=registry,
        evaluator=evaluator,
        clock=clock,
    )

    application = FastAPI()
    application.include_router(
        build_host_router(service)
    )

    return application


def build_agent(
    config: HostAgentConfig,
    sender: HttpHeartbeatSender,
    case: dict[str, Any],
) -> HostAgent:
    """Build one deterministic Agent heartbeat cycle."""
    observed_at = datetime.fromisoformat(
        case["observed_at"]
    )

    return HostAgent(
        config=config,
        sender=sender,
        clock=lambda: observed_at,
        host_name_provider=(
            lambda: case["host_name"]
        ),
        address_provider=(
            lambda: case["address"]
        ),
        operating_system_provider=(
            lambda: case[
                "operating_system"
            ]
        ),
        architecture_provider=(
            lambda: case["architecture"]
        ),
        agent_version=case["agent_version"],
        sleeper=lambda seconds: None,
    )


def read_stored_host_count(
    database_path: Path,
) -> int:
    """Return the number of stored SQLite hosts."""
    with sqlite3.connect(
        database_path
    ) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM monitored_hosts
            """
        ).fetchone()

    assert row is not None
    return int(row[0])


def test_agent_registers_host_through_api_and_sqlite(
    tmp_path: Path,
) -> None:
    """Persist one Agent heartbeat through the complete stack."""
    case = INTEGRATION_CASES[
        "initial_heartbeat"
    ]
    observed_at = datetime.fromisoformat(
        case["observed_at"]
    )
    database_path = (
        tmp_path
        / REGISTRY_CASE["database_file"]
    )

    application = build_application(
        database_path,
        clock=lambda: observed_at,
    )

    config = build_agent_config(
        host_id_override=(
            case["host_id_override"]
        )
    )

    with TestClient(application) as client:
        opener = FastApiClientOpener(client)
        sender = HttpHeartbeatSender(
            opener=opener
        )

        heartbeat = build_agent(
            config,
            sender,
            case,
        ).run_once()

        list_response = client.get(
            "/api/v1/hosts"
        )
        detail_response = client.get(
            f"/api/v1/hosts/{heartbeat.host_id}"
        )

    assert heartbeat.host_id == (
        case["host_id_override"]
    )

    assert opener.calls == [
        (
            "POST",
            config.server.heartbeat_url,
            config.server.request_timeout_seconds,
            200,
        )
    ]

    assert list_response.status_code == 200
    assert detail_response.status_code == 200

    hosts = list_response.json()

    assert len(hosts) == 1
    assert detail_response.json() == hosts[0]

    stored_host = hosts[0]

    assert stored_host["host_id"] == (
        case["host_id_override"]
    )
    assert stored_host["host_name"] == (
        case["host_name"]
    )
    assert stored_host["address"] == (
        case["address"]
    )
    assert stored_host["operating_system"] == (
        case["operating_system"]
    )
    assert stored_host["architecture"] == (
        case["architecture"]
    )
    assert stored_host["agent_version"] == (
        case["agent_version"]
    )
    assert stored_host["availability"] == (
        EXPECTED["availability"]
    )
    assert stored_host[
        "heartbeat_age_seconds"
    ] == EXPECTED[
        "heartbeat_age_seconds"
    ]
    assert parse_timestamp(
        stored_host["registered_at"]
    ) == observed_at
    assert parse_timestamp(
        stored_host["last_seen_at"]
    ) == observed_at

    assert database_path.exists()
    assert read_stored_host_count(
        database_path
    ) == EXPECTED["stored_row_count"]


def test_newer_heartbeat_updates_existing_sqlite_host(
    tmp_path: Path,
) -> None:
    """Update one host without creating a duplicate row."""
    initial = INTEGRATION_CASES[
        "initial_heartbeat"
    ]
    updated = INTEGRATION_CASES[
        "updated_heartbeat"
    ]

    initial_time = datetime.fromisoformat(
        initial["observed_at"]
    )
    updated_time = datetime.fromisoformat(
        updated["observed_at"]
    )

    current_time = {
        "value": initial_time,
    }

    database_path = (
        tmp_path
        / REGISTRY_CASE["database_file"]
    )

    application = build_application(
        database_path,
        clock=lambda: current_time["value"],
    )

    config = build_agent_config(
        host_id_override=(
            initial["host_id_override"]
        )
    )

    with TestClient(application) as client:
        opener = FastApiClientOpener(client)
        sender = HttpHeartbeatSender(
            opener=opener
        )

        build_agent(
            config,
            sender,
            initial,
        ).run_once()

        current_time["value"] = updated_time

        build_agent(
            config,
            sender,
            updated,
        ).run_once()

        response = client.get(
            "/api/v1/hosts"
        )

    assert response.status_code == 200

    hosts = response.json()

    assert len(hosts) == 1

    stored_host = hosts[0]

    assert stored_host["host_id"] == (
        initial["host_id_override"]
    )
    assert stored_host["host_name"] == (
        updated["host_name"]
    )
    assert stored_host["address"] == (
        updated["address"]
    )
    assert stored_host["operating_system"] == (
        updated["operating_system"]
    )
    assert stored_host["agent_version"] == (
        updated["agent_version"]
    )

    assert parse_timestamp(
        stored_host["registered_at"]
    ) == initial_time
    assert parse_timestamp(
        stored_host["last_seen_at"]
    ) == updated_time

    assert stored_host["availability"] == (
        EXPECTED["availability"]
    )
    assert stored_host[
        "heartbeat_age_seconds"
    ] == EXPECTED[
        "heartbeat_age_seconds"
    ]

    assert len(opener.calls) == 2
    assert all(
        status_code == 200
        for (
            method,
            url,
            timeout,
            status_code,
        ) in opener.calls
    )

    assert read_stored_host_count(
        database_path
    ) == EXPECTED["stored_row_count"]
