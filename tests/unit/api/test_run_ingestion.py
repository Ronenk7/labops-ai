"""Tests for central remote-run ingestion."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from labops_ai.api import create_app
from labops_ai.api.run_ingestion import (
    RunIngestionService,
)
from labops_ai.diagnostics import (
    DiagnosticBundleWriteError,
    DiagnosticSnapshot,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryEntry,
    RunHistoryStoreError,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit


def valid_payload() -> dict:
    """Return an isolated valid remote report."""
    return deepcopy(
        load_test_fixture(
            "diagnostics/remote_run_payload.json"
        )
    )


def history_entry(
    snapshot: DiagnosticSnapshot,
    archive_path: Path,
) -> RunHistoryEntry:
    """Build one persisted ingestion result."""
    return RunHistoryEntry(
        run_id=77,
        generated_at=snapshot.generated_at,
        host_name=snapshot.host_name,
        overall_status=snapshot.overall_status,
        system_status=(
            snapshot.system_overall_status
        ),
        network_status=(
            snapshot.network_overall_status
        ),
        service_status=(
            snapshot.service_overall_status
        ),
        process_status=(
            snapshot.process_overall_status
        ),
        log_status=snapshot.log_overall_status,
        active_incident_count=(
            snapshot.active_incident_count
        ),
        resolved_incident_count=(
            snapshot.resolved_incident_count
        ),
        bundle_id="remote-bundle-77",
        archive_path=str(archive_path),
    )


@dataclass
class FakeBundleWriter:
    """Record snapshots written by ingestion."""

    archive_path: Path
    fail: bool = False
    snapshots: list[DiagnosticSnapshot] = field(
        default_factory=list
    )

    def write(
        self,
        snapshot: DiagnosticSnapshot,
    ):
        if self.fail:
            raise DiagnosticBundleWriteError(
                "Simulated bundle failure."
            )

        self.snapshots.append(snapshot)
        self.archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.archive_path.write_bytes(b"zip")

        return SimpleNamespace(
            bundle_id="remote-bundle-77",
            archive_path=self.archive_path,
        )


@dataclass
class FakeHistoryStore:
    """Record snapshots stored by ingestion."""

    archive_path: Path
    fail: bool = False
    snapshots: list[DiagnosticSnapshot] = field(
        default_factory=list
    )

    def save(
        self,
        snapshot: DiagnosticSnapshot,
        *,
        bundle_id: str,
        archive_path: str | Path,
    ) -> RunHistoryEntry:
        if self.fail:
            raise RunHistoryStoreError(
                "Simulated history failure."
            )

        assert bundle_id == "remote-bundle-77"
        assert Path(archive_path) == self.archive_path

        self.snapshots.append(snapshot)

        return history_entry(
            snapshot,
            self.archive_path,
        )


def build_service(
    tmp_path: Path,
    *,
    writer_fail: bool = False,
    history_fail: bool = False,
) -> tuple[
    RunIngestionService,
    FakeBundleWriter,
    FakeHistoryStore,
]:
    """Build an isolated ingestion service."""
    archive_path = (
        tmp_path
        / "bundles"
        / "remote-bundle-77.zip"
    )
    writer = FakeBundleWriter(
        archive_path=archive_path,
        fail=writer_fail,
    )
    store = FakeHistoryStore(
        archive_path=archive_path,
        fail=history_fail,
    )

    return (
        RunIngestionService(
            bundle_writer=writer,
            history_store=store,
        ),
        writer,
        store,
    )


def test_ingests_bundle_and_history(
    tmp_path: Path,
) -> None:
    """Write the ZIP before storing SQLite history."""
    service, writer, store = build_service(
        tmp_path
    )

    entry = service.ingest(valid_payload())

    assert entry.run_id == 77
    assert entry.host_name == "lab-node-02"
    assert entry.overall_status is (
        HealthStatus.HEALTHY
    )
    assert len(writer.snapshots) == 1
    assert len(store.snapshots) == 1


def test_removes_bundle_when_history_fails(
    tmp_path: Path,
) -> None:
    """Avoid orphaned ZIP files after SQLite failure."""
    service, writer, _ = build_service(
        tmp_path,
        history_fail=True,
    )

    with pytest.raises(
        RunHistoryStoreError,
        match="Simulated history failure",
    ):
        service.ingest(valid_payload())

    assert not writer.archive_path.exists()


def test_api_accepts_remote_run(
    tmp_path: Path,
) -> None:
    """Expose successful central ingestion."""
    service, _, _ = build_service(tmp_path)
    client = TestClient(
        create_app(
            run_ingestion_service=service
        )
    )

    response = client.post(
        "/api/v1/runs/ingest",
        json={
            "diagnostics": valid_payload()
        },
    )

    assert response.status_code == 201
    assert response.json()["run_id"] == 77
    assert response.json()["host_name"] == (
        "lab-node-02"
    )


def test_api_rejects_invalid_remote_run(
    tmp_path: Path,
) -> None:
    """Map invalid diagnostics to HTTP 422."""
    service, _, _ = build_service(tmp_path)
    client = TestClient(
        create_app(
            run_ingestion_service=service
        )
    )

    response = client.post(
        "/api/v1/runs/ingest",
        json={
            "diagnostics": {
                "schema_version": 999
            }
        },
    )

    assert response.status_code == 422
    assert "schema_version" in (
        response.json()["detail"]
    )


def test_api_maps_storage_failure(
    tmp_path: Path,
) -> None:
    """Map central persistence failure to HTTP 503."""
    service, _, _ = build_service(
        tmp_path,
        history_fail=True,
    )
    client = TestClient(
        create_app(
            run_ingestion_service=service
        )
    )

    response = client.post(
        "/api/v1/runs/ingest",
        json={
            "diagnostics": valid_payload()
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Remote monitoring run could not "
        "be stored."
    )
