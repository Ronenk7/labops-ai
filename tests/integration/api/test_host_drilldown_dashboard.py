"""Integration tests for the Host drill-down dashboard."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labops_ai.api.app import app


pytestmark = pytest.mark.integration


def test_serves_host_drilldown_page() -> None:
    """Return the dedicated Host workspace HTML."""
    response = TestClient(app).get(
        "/dashboard/hosts/host-001"
    )

    assert response.status_code == 200
    assert "Host intelligence workspace" in response.text
    assert 'id="host-name"' in response.text
    assert 'id="host-runs-body"' in response.text
    assert "dashboard-host-detail.js" in response.text


def test_serves_host_drilldown_assets() -> None:
    """Expose the Host page CSS and JavaScript."""
    client = TestClient(app)

    css_response = client.get(
        "/dashboard-assets/dashboard-host-detail.css"
    )
    js_response = client.get(
        "/dashboard-assets/dashboard-host-detail.js"
    )

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert ".host-detail-main" in css_response.text
    assert "/api/v1/hosts/" in js_response.text
    assert "/overview" in js_response.text
    assert "/archive" in js_response.text


def test_registers_drilldown_and_archive_api_routes() -> None:
    """Expose both Host overview and ZIP download APIs."""
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert (
        "/api/v1/hosts/{host_id}/overview"
        in paths
    )
    assert (
        "/api/v1/runs/{run_id}/archive"
        in paths
    )


def test_fleet_drawer_links_to_full_host_view() -> None:
    """Allow navigation from the Fleet Drawer."""
    response = TestClient(app).get(
        "/dashboard-assets/dashboard-hosts-page.js"
    )

    assert response.status_code == 200
    assert "Open full Host view" in response.text
    assert "/dashboard/hosts/" in response.text
