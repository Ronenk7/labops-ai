"""Integration tests for host routes in the main API."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from labops_ai.api.app import app


pytestmark = pytest.mark.integration


def test_main_app_registers_multi_host_routes() -> None:
    """Expose host routes without hiding suggestions."""
    client = TestClient(app)

    openapi_response = client.get("/openapi.json")

    assert openapi_response.status_code == 200

    paths = openapi_response.json()["paths"]

    assert "/api/v1/hosts" in paths
    assert "/api/v1/hosts/heartbeat" in paths
    assert "/api/v1/hosts/{host_id}" in paths
    assert "/api/v1/hosts/suggestions" in paths

    suggestions_response = client.get(
        "/api/v1/hosts/suggestions"
    )

    assert suggestions_response.status_code == 200
    assert isinstance(suggestions_response.json(), list)
