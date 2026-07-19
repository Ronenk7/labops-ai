"""Unit tests for writing complete diagnostic ZIP bundles."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import pytest

from labops_ai.diagnostics import (
    DiagnosticBundleCollectionConfig,
    DiagnosticBundleConfig,
    DiagnosticBundleFilesConfig,
    DiagnosticBundleOutputConfig,
)
from labops_ai.diagnostics.diagnostic_bundle_writer import (
    DiagnosticBundleWriteError,
    DiagnosticBundleWriteResult,
    DiagnosticBundleWriter,
)
from tests.support.diagnostic_snapshot_factory import (
    build_test_diagnostic_snapshot,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "diagnostics/diagnostic_bundle_writer_cases.json"
)


def build_config(
    output_directory: Path,
    *,
    include_json_report: bool = True,
    include_text_report: bool = True,
    include_incident_snapshot: bool = True,
) -> DiagnosticBundleConfig:
    """Build controlled diagnostic bundle configuration."""
    return DiagnosticBundleConfig(
        output=DiagnosticBundleOutputConfig(
            directory=str(output_directory),
            archive_prefix="labops-diagnostic",
            timestamp_format="%Y%m%dT%H%M%SZ",
        ),
        collection=DiagnosticBundleCollectionConfig(
            include_json_report=include_json_report,
            include_text_report=include_text_report,
            include_incident_snapshot=(
                include_incident_snapshot
            ),
        ),
        files=DiagnosticBundleFilesConfig(
            manifest_name=CASES["manifest_name"],
            json_report_name=CASES["json_report_name"],
            text_report_name=CASES["text_report_name"],
            incident_snapshot_name=(
                CASES["incident_snapshot_name"]
            ),
        ),
    )


def read_json_file(
    archive: ZipFile,
    file_name: str,
) -> dict:
    """Read one JSON object from a ZIP archive."""
    return json.loads(
        archive.read(file_name).decode("utf-8")
    )


class TestDiagnosticBundleWriter:
    """Test complete diagnostic archive writing."""

    def test_writes_expected_archive_name(
        self,
        tmp_path: Path,
    ) -> None:
        writer = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        )

        result = writer.write(
            build_test_diagnostic_snapshot()
        )

        assert isinstance(
            result,
            DiagnosticBundleWriteResult,
        )
        assert result.bundle_id == CASES["bundle_id"]
        assert result.archive_path.name == (
            CASES["archive_name"]
        )
        assert result.archive_path.is_file()

    def test_includes_all_configured_files(
        self,
        tmp_path: Path,
    ) -> None:
        result = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        ).write(build_test_diagnostic_snapshot())

        with ZipFile(result.archive_path) as archive:
            assert set(archive.namelist()) == set(
                CASES["all_archive_files"]
            )

    def test_writes_complete_manifest(
        self,
        tmp_path: Path,
    ) -> None:
        result = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        ).write(build_test_diagnostic_snapshot())

        with ZipFile(result.archive_path) as archive:
            manifest = read_json_file(
                archive,
                CASES["manifest_name"],
            )

        assert manifest["schema_version"] == 1
        assert manifest["bundle_id"] == CASES["bundle_id"]
        assert manifest["generated_at"] == (
            CASES["generated_at"]
        )
        assert manifest["host_name"] == (
            CASES["host_name"]
        )
        assert len(manifest["artifacts"]) == 3

    def test_manifest_hashes_and_sizes_match_files(
        self,
        tmp_path: Path,
    ) -> None:
        result = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        ).write(build_test_diagnostic_snapshot())

        with ZipFile(result.archive_path) as archive:
            manifest = read_json_file(
                archive,
                CASES["manifest_name"],
            )

            for artifact in manifest["artifacts"]:
                content = archive.read(
                    artifact["file_name"]
                )

                assert len(content) == (
                    artifact["size_bytes"]
                )
                assert sha256(content).hexdigest() == (
                    artifact["sha256"]
                )

    def test_writes_incident_snapshot(
        self,
        tmp_path: Path,
    ) -> None:
        result = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        ).write(build_test_diagnostic_snapshot())

        with ZipFile(result.archive_path) as archive:
            incidents = read_json_file(
                archive,
                CASES["incident_snapshot_name"],
            )

        assert incidents["schema_version"] == 1
        assert incidents["active_count"] == (
            CASES["active_incidents"]
        )
        assert incidents["resolved_count"] == (
            CASES["resolved_incidents"]
        )
        assert len(incidents["records"]) == (
            CASES["incident_count"]
        )

    def test_respects_disabled_optional_artifacts(
        self,
        tmp_path: Path,
    ) -> None:
        result = DiagnosticBundleWriter(
            config=build_config(
                tmp_path,
                include_json_report=False,
                include_text_report=True,
                include_incident_snapshot=False,
            )
        ).write(build_test_diagnostic_snapshot())

        with ZipFile(result.archive_path) as archive:
            manifest = read_json_file(
                archive,
                CASES["manifest_name"],
            )

            assert set(archive.namelist()) == {
                CASES["manifest_name"],
                CASES["text_report_name"],
            }

        assert len(manifest["artifacts"]) == 1
        assert manifest["artifacts"][0][
            "artifact_type"
        ] == "TEXT_REPORT"

    def test_rejects_existing_archive(
        self,
        tmp_path: Path,
    ) -> None:
        writer = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        )
        snapshot = build_test_diagnostic_snapshot()

        writer.write(snapshot)

        with pytest.raises(
            DiagnosticBundleWriteError,
            match="already exists",
        ):
            writer.write(snapshot)

    def test_rejects_invalid_snapshot(
        self,
        tmp_path: Path,
    ) -> None:
        writer = DiagnosticBundleWriter(
            config=build_config(tmp_path)
        )

        with pytest.raises(
            TypeError,
            match="DiagnosticSnapshot",
        ):
            writer.write(object())

    def test_rejects_invalid_configuration(self) -> None:
        with pytest.raises(
            TypeError,
            match="DiagnosticBundleConfig",
        ):
            DiagnosticBundleWriter(config=object())

    def test_reports_invalid_output_directory(
        self,
        tmp_path: Path,
    ) -> None:
        output_file = tmp_path / "not-a-directory"
        output_file.write_text(
            "occupied",
            encoding="utf-8",
        )

        writer = DiagnosticBundleWriter(
            config=build_config(output_file)
        )

        with pytest.raises(
            DiagnosticBundleWriteError,
            match="output directory",
        ):
            writer.write(
                build_test_diagnostic_snapshot()
            )