"""Integration tests for monitored-host dashboard assets."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labops_ai.api.app import app


pytestmark = pytest.mark.integration


def test_dashboard_exposes_monitored_hosts_section() -> None:
    """Expose complete Host fleet markup and assets."""
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200

    expected_tokens = (
        "Monitored Hosts",
        'id="monitored-hosts"',
        'id="host-fleet-total"',
        'id="host-fleet-online"',
        'id="host-fleet-stale"',
        'id="host-fleet-offline"',
        'id="host-fleet-filter"',
        'id="host-fleet-table-body"',
        "dashboard-hosts.css",
        "dashboard-hosts.js",
    )

    for token in expected_tokens:
        assert token in response.text


def test_monitored_host_assets_are_served() -> None:
    """Serve Host fleet behavior and presentation assets."""
    client = TestClient(app)

    stylesheet = client.get(
        "/dashboard-assets/dashboard-hosts.css"
    )
    script = client.get(
        "/dashboard-assets/dashboard-hosts.js"
    )

    assert stylesheet.status_code == 200
    assert script.status_code == 200

    stylesheet_tokens = (
        ".host-fleet",
        ".host-status--online",
        ".host-status--stale",
        ".host-status--offline",
        "@media",
    )

    for token in stylesheet_tokens:
        assert token in stylesheet.text

    script_tokens = (
        'fetch(',
        '"/api/v1/hosts"',
        "renderHosts",
        "heartbeat_age_seconds",
        "last_seen_at",
        "ONLINE",
        "STALE",
        "OFFLINE",
        "AbortController",
    )

    for token in script_tokens:
        assert token in script.text
