# Integration tests for the Run Details dashboard.
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labops_ai.api.app import app


pytestmark = pytest.mark.integration


def test_serves_run_details_page() -> None:
    "Return the human-readable monitoring-run page."
    response = TestClient(app).get(
        "/dashboard/runs/274"
    )

    assert response.status_code == 200
    assert "Monitoring evidence" in response.text
    assert 'id="run-title"' in response.text
    assert 'id="run-system-metrics"' in response.text
    assert "dashboard-run-detail.js" in response.text


def test_serves_run_details_assets() -> None:
    "Expose the Run Details CSS and JavaScript."
    client = TestClient(app)

    css_response = client.get(
        "/dashboard-assets/dashboard-run-detail.css"
    )
    js_response = client.get(
        "/dashboard-assets/dashboard-run-detail.js"
    )

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert ".run-detail-main" in css_response.text
    assert "/api/v1/runs/" in js_response.text
    assert "/details" in js_response.text
    assert "/archive" in js_response.text


def test_rejects_invalid_run_dashboard_identifier() -> None:
    "Require a positive integer in the Run route."
    response = TestClient(app).get(
        "/dashboard/runs/0"
    )

    assert response.status_code == 422


def test_host_dashboard_links_to_readable_run() -> None:
    "Expose readable Details without Raw JSON controls."
    response = TestClient(app).get(
        "/dashboard-assets/dashboard-host-detail.js"
    )

    assert response.status_code == 200
    assert "/dashboard/runs/" in response.text
    assert '"Raw JSON"' not in response.text
    assert "/api/v1/runs/" in response.text
