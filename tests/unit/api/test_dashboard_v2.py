"""Tests for dashboard analytics and reporting."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from labops_ai.api import (
    DashboardAnalyticsService,
    RunHistoryApiService,
    RunHistoryCsvReportBuilder,
    create_app,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry


pytestmark = pytest.mark.unit
NOW = datetime(
    2026,
    7,
    19,
    20,
    0,
    tzinfo=timezone.utc,
)


def build_entry(
    run_id: int,
    status: HealthStatus,
) -> RunHistoryEntry:
    """Build one deterministic monitoring entry."""
    return RunHistoryEntry(
        run_id=run_id,
        generated_at=NOW,
        host_name="Kukner7",
        overall_status=status,
        system_status=status,
        network_status=HealthStatus.HEALTHY,
        service_status=status,
        process_status=HealthStatus.HEALTHY,
        log_status=HealthStatus.HEALTHY,
        active_incident_count=(
            1
            if status is HealthStatus.CRITICAL
            else 0
        ),
        resolved_incident_count=0,
        bundle_id=f"bundle-{run_id}",
        archive_path=f"/tmp/bundle-{run_id}.zip",
    )


@dataclass
class FakeReader:
    """Provide deterministic history reads."""

    entries: tuple[RunHistoryEntry, ...]

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        return next(
            (
                entry
                for entry in self.entries
                if entry.run_id == run_id
            ),
            None,
        )

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        return self.entries[0] if self.entries else None

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        matches = tuple(
            entry
            for entry in self.entries
            if status is None
            or entry.overall_status is status
        )
        return matches[:limit]


def build_reader() -> FakeReader:
    return FakeReader(
        entries=(
            build_entry(3, HealthStatus.HEALTHY),
            build_entry(2, HealthStatus.HEALTHY),
            build_entry(1, HealthStatus.CRITICAL),
        )
    )


def test_calculates_dashboard_overview() -> None:
    overview = DashboardAnalyticsService(
        reader=build_reader()
    ).build_overview(limit=100)

    assert overview.sample_size == 3
    assert overview.health_score == 66.7
    assert overview.current_healthy_streak == 2
    assert overview.active_incident_total == 1
    assert overview.status_distribution.healthy == 2
    assert overview.status_distribution.critical == 1


def test_dashboard_overview_endpoint() -> None:
    service = RunHistoryApiService(
        reader=build_reader()
    )
    client = TestClient(create_app(service))

    response = client.get(
        "/api/v1/dashboard/overview"
    )

    assert response.status_code == 200
    assert response.json()["sample_size"] == 3
    assert response.json()["health_score"] == 66.7


def test_csv_report_endpoint() -> None:
    service = RunHistoryApiService(
        reader=build_reader()
    )
    client = TestClient(create_app(service))

    response = client.get(
        "/api/v1/runs/export.csv"
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers[
        "content-type"
    ]
    assert "Run ID" in response.text
    assert "bundle-3" in response.text


def test_csv_builder_rejects_invalid_entry() -> None:
    with pytest.raises(TypeError):
        RunHistoryCsvReportBuilder.build(
            [object()]
        )


def test_professional_dashboard_assets() -> None:
    service = RunHistoryApiService(
        reader=build_reader()
    )
    client = TestClient(create_app(service))

    dashboard = client.get("/dashboard")
    stylesheet = client.get(
        "/dashboard-assets/dashboard.css"
    )
    script = client.get(
        "/dashboard-assets/dashboard.js"
    )
    pro_stylesheet = client.get(
        "/dashboard-assets/dashboard-pro.css"
    )
    pro_script = client.get(
        "/dashboard-assets/dashboard-pro.js"
    )

    assert dashboard.status_code == 200
    assert "Operations overview" in dashboard.text
    assert "Incident Center" in dashboard.text
    assert "incident-filters" in dashboard.text
    assert "host-suggestions-button" in dashboard.text
    assert stylesheet.status_code == 200
    assert "--orange" in stylesheet.text
    assert "Incident Center" in stylesheet.text
    assert script.status_code == 200
    assert "renderTrend" in script.text
    assert "renderIncidents" in script.text
    assert "/api/v1/incidents/summary" in script.text
    assert "/api/v1/hosts/suggestions" in script.text
    assert "/details" in script.text
    assert "renderRunDetails" in script.text
    assert pro_stylesheet.status_code == 200
    assert "Run Story" in pro_stylesheet.text
    assert "live-chart-tooltip" in pro_stylesheet.text
    assert pro_script.status_code == 200
    assert "run-story__hero" in pro_script.text
    assert "proUpdateLiveComparison" in pro_script.text
    assert "showLiveChartTooltip" in pro_script.text
