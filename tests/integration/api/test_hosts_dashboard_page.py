"""Integration tests for the dedicated Host Fleet page."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labops_ai.api.app import app


pytestmark = pytest.mark.integration


def test_serves_dedicated_hosts_dashboard() -> None:
    """Serve the complete multi-host operations page."""
    client = TestClient(app)

    response = client.get("/dashboard/hosts")

    assert response.status_code == 200

    expected_tokens = (
        "Fleet command center",
        "Monitored infrastructure",
        'id="fleet-total"',
        'id="fleet-online"',
        'id="fleet-stale"',
        'id="fleet-offline"',
        'id="fleet-host-grid"',
        'id="host-drawer"',
        "dashboard-hosts-page.css",
        "dashboard-hosts-page.js",
    )

    for token in expected_tokens:
        assert token in response.text


def test_serves_hosts_dashboard_assets() -> None:
    """Serve Fleet-specific CSS and JavaScript."""
    client = TestClient(app)

    stylesheet = client.get(
        "/dashboard-assets/dashboard-hosts-page.css"
    )
    script = client.get(
        "/dashboard-assets/dashboard-hosts-page.js"
    )

    assert stylesheet.status_code == 200
    assert script.status_code == 200

    for token in (
        ".fleet-hero",
        ".fleet-summary",
        ".host-card",
        ".host-drawer",
        ".host-availability--online",
        ".host-availability--stale",
        ".host-availability--offline",
    ):
        assert token in stylesheet.text

    for token in (
        'fetch(',
        '"/api/v1/hosts"',
        "renderHosts",
        "openHostDrawer",
        "heartbeat_age_seconds",
        "AbortController",
        "REFRESH_INTERVAL_SECONDS",
    ):
        assert token in script.text


def test_overview_links_to_host_fleet() -> None:
    """Expose Host Fleet navigation from the overview."""
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'href="/dashboard/hosts"' in response.text
    assert "Host Fleet" in response.text
