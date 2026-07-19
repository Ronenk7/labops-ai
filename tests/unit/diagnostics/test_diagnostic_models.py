"""Unit tests for diagnostic bundle metadata models."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import pytest

from labops_ai.diagnostics import (
    DiagnosticArtifactRecord,
    DiagnosticArtifactType,
    DiagnosticBundleManifest,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_models_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse one ISO 8601 fixture datetime."""
    return datetime.fromisoformat(value)


def build_artifact(
    artifact_type: DiagnosticArtifactType = (
        DiagnosticArtifactType.JSON_REPORT
    ),
    file_name: str = "diagnostic_report.json",
) -> DiagnosticArtifactRecord:
    """Build one valid diagnostic artifact."""
    case = CASES["artifact"]

    return DiagnosticArtifactRecord(
        artifact_type=artifact_type,
        file_name=file_name,
        size_bytes=case["size_bytes"],
        sha256=case["sha256"],
    )


def build_manifest(
    artifacts: tuple[DiagnosticArtifactRecord, ...],
) -> DiagnosticBundleManifest:
    """Build one valid diagnostic manifest."""
    case = CASES["manifest"]

    return DiagnosticBundleManifest(
        schema_version=case["schema_version"],
        bundle_id=case["bundle_id"],
        generated_at=parse_datetime(case["generated_at"]),
        host_name=case["host_name"],
        artifacts=artifacts,
    )


class TestDiagnosticArtifactRecord:
    """Test metadata for one archived artifact."""

    def test_accepts_and_normalizes_valid_artifact(
        self,
    ) -> None:
        artifact = build_artifact()

        assert artifact.artifact_type is (
            DiagnosticArtifactType.JSON_REPORT
        )
        assert artifact.sha256 == "a" * 64
        assert artifact.size_bytes == 1234

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_sizes"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_artifact_size(
        self,
        case: dict[str, Any],
    ) -> None:
        artifact = CASES["artifact"]

        with pytest.raises((TypeError, ValueError)):
            DiagnosticArtifactRecord(
                artifact_type=(
                    DiagnosticArtifactType.JSON_REPORT
                ),
                file_name=artifact["file_name"],
                size_bytes=case["value"],
                sha256=artifact["sha256"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_hashes"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_sha256(
        self,
        case: dict[str, Any],
    ) -> None:
        artifact = CASES["artifact"]

        with pytest.raises((TypeError, ValueError)):
            DiagnosticArtifactRecord(
                artifact_type=(
                    DiagnosticArtifactType.JSON_REPORT
                ),
                file_name=artifact["file_name"],
                size_bytes=artifact["size_bytes"],
                sha256=case["value"],
            )


class TestDiagnosticBundleManifest:
    """Test complete diagnostic bundle manifests."""

    def test_accepts_and_normalizes_valid_manifest(
        self,
    ) -> None:
        manifest = build_manifest(
            artifacts=(build_artifact(),)
        )

        assert manifest.schema_version == 1
        assert manifest.generated_at.tzinfo is timezone.utc
        assert len(manifest.artifacts) == 1

    def test_rejects_datetime_without_timezone(self) -> None:
        case = CASES["manifest"]

        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            DiagnosticBundleManifest(
                schema_version=1,
                bundle_id=case["bundle_id"],
                generated_at=datetime(
                    2026,
                    7,
                    19,
                    10,
                    30,
                ),
                host_name=case["host_name"],
                artifacts=(build_artifact(),),
            )

    def test_rejects_empty_artifact_collection(self) -> None:
        with pytest.raises(
            ValueError,
            match="at least one artifact",
        ):
            build_manifest(artifacts=())

    def test_rejects_duplicate_artifact_names(self) -> None:
        first = build_artifact()
        second = build_artifact(
            artifact_type=(
                DiagnosticArtifactType.TEXT_REPORT
            ),
            file_name=first.file_name.upper(),
        )

        with pytest.raises(
            ValueError,
            match="names must be unique",
        ):
            build_manifest(
                artifacts=(first, second)
            )

    def test_rejects_duplicate_artifact_types(self) -> None:
        first = build_artifact()
        second = replace(
            first,
            file_name="second_report.json",
        )

        with pytest.raises(
            ValueError,
            match="types must be unique",
        ):
            build_manifest(
                artifacts=(first, second)
            )

    def test_rejects_invalid_schema_version(self) -> None:
        case = CASES["manifest"]

        with pytest.raises(
            ValueError,
            match="greater than zero",
        ):
            DiagnosticBundleManifest(
                schema_version=0,
                bundle_id=case["bundle_id"],
                generated_at=parse_datetime(
                    case["generated_at"]
                ),
                host_name=case["host_name"],
                artifacts=(build_artifact(),),
            )