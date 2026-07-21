"""Tests for secure diagnostic ZIP downloads."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

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
    21,
    13,
    0,
    tzinfo=timezone.utc,
)


@dataclass
class FakeHistoryReader:
    """Provide one deterministic monitoring run."""

    entry: RunHistoryEntry

    def get_by_id(
        self,
        run_id: int,
    ) -> RunHistoryEntry | None:
        """Return one matching run."""
        return self.entry if run_id == self.entry.run_id else None

    def get_latest(
        self,
        *,
        host_name: str | None = None,
    ) -> RunHistoryEntry | None:
        """Return the stored run."""
        return self.entry

    def list_recent(
        self,
        *,
        limit: int = 20,
        status: HealthStatus | None = None,
        host_name: str | None = None,
    ) -> tuple[RunHistoryEntry, ...]:
        """Return the stored run."""
        return (self.entry,)

    def suggest_hosts(
        self,
        *,
        prefix: str = "",
        limit: int = 10,
    ) -> tuple[str, ...]:
        """Return one Host suggestion."""
        return (self.entry.host_name,)


def build_config(
    output_directory: Path,
) -> DiagnosticBundleConfig:
    """Build a deterministic archive configuration."""
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


def build_entry(
    archive_path: Path,
) -> RunHistoryEntry:
    """Build run metadata pointing at the ZIP."""
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


def build_client(
    output_directory: Path,
    archive_path: Path,
) -> TestClient:
    """Create an API backed by one real ZIP file."""
    history_service = RunHistoryApiService(
        reader=FakeHistoryReader(
            build_entry(archive_path)
        )
    )
    details_service = RunDetailsApiService(
        history_service=history_service,
        archive_reader=DiagnosticArchiveReader(
            config=build_config(output_directory)
        ),
    )

    return TestClient(
        create_app(
            history_service=history_service,
            run_details_service=details_service,
        )
    )


def test_downloads_validated_archive(
    tmp_path: Path,
) -> None:
    """Return the original diagnostic ZIP bytes."""
    output_directory = tmp_path / "bundles"
    output_directory.mkdir()

    archive_path = output_directory / "run-18.zip"

    with ZipFile(archive_path, mode="w") as archive:
        archive.writestr("evidence.txt", "LabOps AI")

    response = build_client(
        output_directory,
        archive_path,
    ).get(
        "/api/v1/runs/18/archive"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/zip"
    )
    assert "run-18.zip" in response.headers[
        "content-disposition"
    ]
    assert response.content == archive_path.read_bytes()


def test_returns_404_for_missing_run(
    tmp_path: Path,
) -> None:
    """Return HTTP 404 for an unknown run identifier."""
    output_directory = tmp_path / "bundles"
    output_directory.mkdir()

    archive_path = output_directory / "run-18.zip"

    with ZipFile(archive_path, mode="w"):
        pass

    response = build_client(
        output_directory,
        archive_path,
    ).get(
        "/api/v1/runs/999/archive"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Monitoring run 999 was not found."
    )


def test_rejects_archive_outside_bundle_directory(
    tmp_path: Path,
) -> None:
    """Prevent downloads outside the configured directory."""
    output_directory = tmp_path / "bundles"
    output_directory.mkdir()

    outside_archive = tmp_path / "outside.zip"

    with ZipFile(outside_archive, mode="w"):
        pass

    response = build_client(
        output_directory,
        outside_archive,
    ).get(
        "/api/v1/runs/18/archive"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Diagnostic archive is outside "
        "the configured bundle directory."
    )
