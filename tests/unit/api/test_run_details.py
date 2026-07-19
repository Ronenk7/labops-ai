"""Tests for ZIP-backed monitoring run details."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from labops_ai.api import (
    DiagnosticArchiveReader,
    RunDetailsApiService,
    RunHistoryApiService,
    create_app,
)
from labops_ai.diagnostics import (
    DiagnosticBundleCollectionConfig,
    DiagnosticBundleConfig,
    DiagnosticBundleFilesConfig,
    DiagnosticBundleOutputConfig,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry


pytestmark = pytest.mark.unit
NOW = datetime(
    2026,
    7,
    20,
    1,
    30,
    tzinfo=timezone.utc,
)


@dataclass
class FakeHistoryReader:
    """Return one deterministic monitoring run."""

    entry: RunHistoryEntry

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        return self.entry if run_id == self.entry.run_id else None

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        return self.entry

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        return (self.entry,)

    def suggest_hosts(
        self,
        *,
        prefix: str = "",
        limit: int = 10,
    ) -> tuple[str, ...]:
        return (self.entry.host_name,)


def build_config(
    output_directory: Path,
) -> DiagnosticBundleConfig:
    """Build deterministic ZIP configuration."""
    return DiagnosticBundleConfig(
        output=DiagnosticBundleOutputConfig(
            directory=str(output_directory),
            archive_prefix="test-diagnostic",
            timestamp_format="%Y%m%dT%H%M%SZ",
        ),
        collection=DiagnosticBundleCollectionConfig(
            include_json_report=True,
            include_text_report=True,
            include_incident_snapshot=True,
        ),
        files=DiagnosticBundleFilesConfig(
            manifest_name="manifest.json",
            json_report_name="diagnostic_report.json",
            text_report_name="diagnostic_report.txt",
            incident_snapshot_name="incidents.json",
        ),
    )


def build_payload() -> dict[str, object]:
    """Build one realistic diagnostic JSON payload."""
    return {
        "schema_version": 1,
        "generated_at": NOW.isoformat(),
        "host_name": "Kukner7",
        "overall_status": "HEALTHY",
        "summary": {
            "active_incidents": 0,
            "resolved_incidents": 0,
            "system_status": "HEALTHY",
            "network_status": "HEALTHY",
            "service_status": "HEALTHY",
            "process_status": "HEALTHY",
            "log_status": "HEALTHY",
        },
        "system": {
            "overall_status": "HEALTHY",
            "metrics": [
                {
                    "metric_name": "cpu",
                    "label": "CPU usage",
                    "value_percent": 14.25,
                    "health_status": "HEALTHY",
                }
            ],
        },
        "network": {
            "overall_status": "HEALTHY",
            "checks": [],
        },
        "services": {
            "overall_status": "HEALTHY",
            "records": [],
        },
        "processes": {
            "overall_status": "HEALTHY",
            "records": [],
        },
        "logs": {
            "overall_status": "HEALTHY",
            "records": [],
        },
        "incidents": {
            "active_count": 0,
            "resolved_count": 0,
            "records": [],
        },
    }


def write_archive(
    output_directory: Path,
) -> Path:
    """Write a real diagnostic ZIP for testing."""
    output_directory.mkdir(parents=True)
    archive_path = output_directory / "run.zip"

    with ZipFile(
        archive_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "diagnostic_report.json",
            json.dumps(build_payload()),
        )

    return archive_path


def build_entry(
    archive_path: Path,
) -> RunHistoryEntry:
    """Build run metadata pointing at the real ZIP."""
    return RunHistoryEntry(
        run_id=18,
        generated_at=NOW,
        host_name="Kukner7",
        overall_status=HealthStatus.HEALTHY,
        system_status=HealthStatus.HEALTHY,
        network_status=HealthStatus.HEALTHY,
        service_status=HealthStatus.HEALTHY,
        process_status=HealthStatus.HEALTHY,
        log_status=HealthStatus.HEALTHY,
        active_incident_count=0,
        resolved_incident_count=0,
        bundle_id="bundle-18",
        archive_path=str(archive_path),
    )


def test_reads_real_json_from_zip(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "bundles"
    archive_path = write_archive(output_directory)

    payload = DiagnosticArchiveReader(
        config=build_config(output_directory)
    ).read(archive_path)

    assert payload["host_name"] == "Kukner7"
    assert (
        payload["system"]["metrics"][0]["value_percent"]
        == 14.25
    )


def test_run_details_endpoint_reads_zip(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "bundles"
    archive_path = write_archive(output_directory)
    entry = build_entry(archive_path)

    history_service = RunHistoryApiService(
        reader=FakeHistoryReader(entry)
    )
    details_service = RunDetailsApiService(
        history_service=history_service,
        archive_reader=DiagnosticArchiveReader(
            config=build_config(output_directory)
        ),
    )

    client = TestClient(
        create_app(
            history_service=history_service,
            run_details_service=details_service,
        )
    )

    response = client.get(
        "/api/v1/runs/18/details"
    )

    assert response.status_code == 200
    assert response.json()["run"]["run_id"] == 18
    assert (
        response.json()["diagnostics"]["system"]
        ["metrics"][0]["label"]
        == "CPU usage"
    )
