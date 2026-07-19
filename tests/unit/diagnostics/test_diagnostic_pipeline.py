"""Unit tests for diagnostic bundle orchestration."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from labops_ai.diagnostics import (
    DiagnosticArtifactRecord,
    DiagnosticArtifactType,
    DiagnosticBundleManifest,
    DiagnosticBundleWriteResult,
)
from labops_ai.diagnostics.diagnostic_pipeline import (
    DiagnosticBundlePipeline,
    DiagnosticBundlePipelineResult,
)
from labops_ai.health_status import HealthStatus
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_pipeline_cases.json"
)


class FakeSnapshotBuilder:
    """Return a controlled snapshot result."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.received: dict[str, object] | None = None

    def build(self, **kwargs: object) -> object:
        """Record supplied values and return the configured result."""
        self.received = dict(kwargs)
        return self.result


class FakeBundleWriter:
    """Return a controlled bundle result."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.received_snapshot: object | None = None

    def write(self, snapshot: object) -> object:
        """Record the snapshot and return the configured result."""
        self.received_snapshot = snapshot
        return self.result


def build_bundle_result() -> DiagnosticBundleWriteResult:
    """Build one valid controlled bundle result."""
    snapshot = build_test_diagnostic_snapshot()
    artifact = DiagnosticArtifactRecord(
        artifact_type=DiagnosticArtifactType.JSON_REPORT,
        file_name=CASES["artifact_file_name"],
        size_bytes=100,
        sha256=CASES["artifact_sha256"],
    )
    manifest = DiagnosticBundleManifest(
        schema_version=1,
        bundle_id=CASES["bundle_id"],
        generated_at=snapshot.generated_at,
        host_name=snapshot.host_name,
        artifacts=(artifact,),
    )

    return DiagnosticBundleWriteResult(
        bundle_id=CASES["bundle_id"],
        archive_path=Path(CASES["archive_path"]),
        manifest=manifest,
    )


def build_valid_pipeline():
    """Build a pipeline with controlled dependencies."""
    snapshot = build_test_diagnostic_snapshot()
    bundle = build_bundle_result()
    builder = FakeSnapshotBuilder(snapshot)
    writer = FakeBundleWriter(bundle)

    pipeline = DiagnosticBundlePipeline(
        snapshot_builder=builder,
        bundle_writer=writer,
        clock=lambda: datetime.fromisoformat(
            CASES["generated_at"]
        ),
        host_name_provider=lambda: (
            f"  {CASES['host_name']}  "
        ),
    )

    return pipeline, builder, writer, snapshot, bundle


def run_pipeline(
    pipeline: DiagnosticBundlePipeline,
) -> DiagnosticBundlePipelineResult:
    """Run a pipeline with controlled domain inputs."""
    return pipeline.run(
        system_metrics={"cpu_percent": 20.0},
        system_statuses={
            "cpu_percent": HealthStatus.HEALTHY
        },
        system_metric_labels={
            "cpu_percent": "CPU usage"
        },
        network_summary=object(),
        service_summary=object(),
        process_summary=object(),
        log_summary=object(),
        incident_state=object(),
    )


class TestDiagnosticBundlePipelineResult:
    """Test complete diagnostic pipeline results."""

    def test_accepts_valid_result(self) -> None:
        snapshot = build_test_diagnostic_snapshot()
        bundle = build_bundle_result()

        result = DiagnosticBundlePipelineResult(
            snapshot=snapshot,
            bundle=bundle,
        )

        assert result.snapshot is snapshot
        assert result.bundle is bundle

    def test_rejects_invalid_snapshot(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            DiagnosticBundlePipelineResult(
                snapshot=object(),
                bundle=build_bundle_result(),
            )

    def test_rejects_invalid_bundle(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticBundleWriteResult",
        ):
            DiagnosticBundlePipelineResult(
                snapshot=build_test_diagnostic_snapshot(),
                bundle=object(),
            )


class TestDiagnosticBundlePipeline:
    """Test complete diagnostic orchestration."""

    @pytest.mark.parametrize(
        "field_name",
        [
            "snapshot_builder",
            "bundle_writer",
            "clock",
            "host_name_provider",
        ],
    )
    def test_rejects_invalid_dependency(
        self,
        field_name: str,
    ) -> None:
        snapshot = build_test_diagnostic_snapshot()
        values: dict[str, Any] = {
            "snapshot_builder": FakeSnapshotBuilder(
                snapshot
            ),
            "bundle_writer": FakeBundleWriter(
                build_bundle_result()
            ),
            "clock": lambda: snapshot.generated_at,
            "host_name_provider": lambda: (
                snapshot.host_name
            ),
        }
        values[field_name] = object()

        with pytest.raises(TypeError):
            DiagnosticBundlePipeline(**values)

    def test_builds_snapshot_and_writes_bundle(self) -> None:
        (
            pipeline,
            builder,
            writer,
            snapshot,
            bundle,
        ) = build_valid_pipeline()

        result = run_pipeline(pipeline)

        assert result.snapshot is snapshot
        assert result.bundle is bundle
        assert writer.received_snapshot is snapshot
        assert builder.received is not None
        assert builder.received["host_name"] == (
            CASES["host_name"]
        )
        assert builder.received["generated_at"] == (
            datetime.fromisoformat(
                CASES["expected_generated_at"]
            )
        )

    def test_normalizes_generation_time_to_utc(self) -> None:
        pipeline, builder, _, _, _ = build_valid_pipeline()

        run_pipeline(pipeline)

        assert builder.received is not None
        generated_at = builder.received["generated_at"]

        assert generated_at.tzinfo is timezone.utc
        assert generated_at.hour == 10

    def test_rejects_naive_clock_result(self) -> None:
        pipeline, _, writer, snapshot, _ = (
            build_valid_pipeline()
        )
        invalid_pipeline = DiagnosticBundlePipeline(
            snapshot_builder=FakeSnapshotBuilder(snapshot),
            bundle_writer=writer,
            clock=lambda: datetime(
                2026,
                7,
                19,
                10,
                30,
            ),
            host_name_provider=lambda: "Kukner7",
        )

        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            run_pipeline(invalid_pipeline)

    @pytest.mark.parametrize(
        "host_name",
        [None, 123, "   "],
    )
    def test_rejects_invalid_host_name(
        self,
        host_name: object,
    ) -> None:
        pipeline, builder, writer, _, _ = (
            build_valid_pipeline()
        )
        invalid_pipeline = DiagnosticBundlePipeline(
            snapshot_builder=builder,
            bundle_writer=writer,
            clock=lambda: datetime.fromisoformat(
                CASES["generated_at"]
            ),
            host_name_provider=lambda: host_name,
        )

        with pytest.raises((TypeError, ValueError)):
            run_pipeline(invalid_pipeline)

    def test_rejects_invalid_snapshot_builder_result(
        self,
    ) -> None:
        pipeline, _, writer, _, _ = build_valid_pipeline()
        invalid_pipeline = DiagnosticBundlePipeline(
            snapshot_builder=FakeSnapshotBuilder(object()),
            bundle_writer=writer,
            clock=pipeline.clock,
            host_name_provider=pipeline.host_name_provider,
        )

        with pytest.raises(
            TypeError,
            match="must return DiagnosticSnapshot",
        ):
            run_pipeline(invalid_pipeline)

    def test_rejects_invalid_bundle_writer_result(
        self,
    ) -> None:
        pipeline, builder, _, _, _ = (
            build_valid_pipeline()
        )
        invalid_pipeline = DiagnosticBundlePipeline(
            snapshot_builder=builder,
            bundle_writer=FakeBundleWriter(object()),
            clock=pipeline.clock,
            host_name_provider=pipeline.host_name_provider,
        )

        with pytest.raises(
            TypeError,
            match="DiagnosticBundleWriteResult",
        ):
            run_pipeline(invalid_pipeline)