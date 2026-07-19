"""Write complete diagnostic snapshots into ZIP archives."""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import (
    ZIP_DEFLATED,
    BadZipFile,
    LargeZipFile,
    ZipFile,
)

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.diagnostics.diagnostic_config import (
    DiagnosticBundleConfig,
)
from labops_ai.diagnostics.diagnostic_models import (
    DiagnosticArtifactRecord,
    DiagnosticArtifactType,
    DiagnosticBundleManifest,
)
from labops_ai.diagnostics.diagnostic_report import (
    build_diagnostic_json,
    build_diagnostic_text,
)
from labops_ai.diagnostics.diagnostic_snapshot import (
    DiagnosticSnapshot,
)


_MANIFEST_SCHEMA_VERSION = 1
_INCIDENT_SNAPSHOT_SCHEMA_VERSION = 1


class DiagnosticBundleWriteError(RuntimeError):
    """Report a failure while writing a diagnostic archive."""


@dataclass(frozen=True, slots=True)
class DiagnosticBundleWriteResult:
    """Represent one successfully written diagnostic bundle."""

    bundle_id: str
    archive_path: Path
    manifest: DiagnosticBundleManifest

    def __post_init__(self) -> None:
        """Validate and normalize the bundle result."""
        if not isinstance(self.bundle_id, str):
            raise TypeError("bundle_id must be a string.")

        normalized_bundle_id = self.bundle_id.strip()

        if not normalized_bundle_id:
            raise ValueError("bundle_id must not be empty.")

        try:
            archive_path = Path(self.archive_path)
        except TypeError as error:
            raise TypeError(
                "archive_path must be path-compatible."
            ) from error

        if archive_path.suffix.casefold() != ".zip":
            raise ValueError(
                "Diagnostic archive path must use a .zip suffix."
            )

        if not isinstance(
            self.manifest,
            DiagnosticBundleManifest,
        ):
            raise TypeError(
                "manifest must be a "
                "DiagnosticBundleManifest instance."
            )

        object.__setattr__(
            self,
            "bundle_id",
            normalized_bundle_id,
        )
        object.__setattr__(
            self,
            "archive_path",
            archive_path,
        )


@dataclass(frozen=True, slots=True)
class _DiagnosticArtifactContent:
    """Keep one artifact record together with its bytes."""

    record: DiagnosticArtifactRecord
    content: bytes


@dataclass(frozen=True, slots=True)
class DiagnosticBundleWriter:
    """Create validated ZIP archives from diagnostic snapshots."""

    config: DiagnosticBundleConfig

    def __post_init__(self) -> None:
        """Validate the writer configuration."""
        if not isinstance(
            self.config,
            DiagnosticBundleConfig,
        ):
            raise TypeError(
                "config must be a DiagnosticBundleConfig instance."
            )

    def write(
        self,
        snapshot: DiagnosticSnapshot,
    ) -> DiagnosticBundleWriteResult:
        """Write one complete diagnostic bundle."""
        if not isinstance(snapshot, DiagnosticSnapshot):
            raise TypeError(
                "snapshot must be a DiagnosticSnapshot instance."
            )

        bundle_id = self._build_bundle_id(snapshot)
        output_directory = self._resolve_output_directory()
        archive_path = (
            output_directory / f"{bundle_id}.zip"
        )

        self._prepare_output_directory(output_directory)

        if archive_path.exists():
            raise DiagnosticBundleWriteError(
                "Diagnostic archive already exists: "
                f"{archive_path}"
            )

        artifacts = self._build_artifacts(snapshot)

        manifest = DiagnosticBundleManifest(
            schema_version=_MANIFEST_SCHEMA_VERSION,
            bundle_id=bundle_id,
            generated_at=snapshot.generated_at,
            host_name=snapshot.host_name,
            artifacts=tuple(
                artifact.record
                for artifact in artifacts
            ),
        )

        manifest_content = self._build_manifest_json(
            manifest
        ).encode("utf-8")

        temporary_path: Path | None = None

        try:
            temporary_path = self._create_temporary_path(
                output_directory=output_directory,
                bundle_id=bundle_id,
            )

            self._write_archive(
                archive_path=temporary_path,
                manifest_content=manifest_content,
                artifacts=artifacts,
            )

            temporary_path.replace(archive_path)
        except (
            OSError,
            ValueError,
            BadZipFile,
            LargeZipFile,
        ) as error:
            raise DiagnosticBundleWriteError(
                "Failed to write diagnostic archive: "
                f"{archive_path}"
            ) from error
        finally:
            if (
                temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink(missing_ok=True)

        return DiagnosticBundleWriteResult(
            bundle_id=bundle_id,
            archive_path=archive_path,
            manifest=manifest,
        )

    def _build_bundle_id(
        self,
        snapshot: DiagnosticSnapshot,
    ) -> str:
        """Build the configured diagnostic bundle identifier."""
        timestamp = snapshot.generated_at.strftime(
            self.config.output.timestamp_format
        )

        return (
            f"{self.config.output.archive_prefix}-"
            f"{timestamp}"
        )

    def _resolve_output_directory(self) -> Path:
        """Resolve an absolute output directory."""
        configured_path = Path(
            self.config.output.directory
        )

        if configured_path.is_absolute():
            return configured_path

        return PROJECT_ROOT / configured_path

    @staticmethod
    def _prepare_output_directory(
        output_directory: Path,
    ) -> None:
        """Create the output directory when necessary."""
        try:
            output_directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as error:
            raise DiagnosticBundleWriteError(
                "Failed to create diagnostic output directory: "
                f"{output_directory}"
            ) from error

        if not output_directory.is_dir():
            raise DiagnosticBundleWriteError(
                "Diagnostic output path is not a directory: "
                f"{output_directory}"
            )

    def _build_artifacts(
        self,
        snapshot: DiagnosticSnapshot,
    ) -> tuple[_DiagnosticArtifactContent, ...]:
        """Build all configured diagnostic artifacts."""
        artifacts: list[_DiagnosticArtifactContent] = []

        if self.config.collection.include_json_report:
            artifacts.append(
                self._create_artifact(
                    artifact_type=(
                        DiagnosticArtifactType.JSON_REPORT
                    ),
                    file_name=(
                        self.config.files.json_report_name
                    ),
                    content=build_diagnostic_json(
                        snapshot
                    ).encode("utf-8"),
                )
            )

        if self.config.collection.include_text_report:
            artifacts.append(
                self._create_artifact(
                    artifact_type=(
                        DiagnosticArtifactType.TEXT_REPORT
                    ),
                    file_name=(
                        self.config.files.text_report_name
                    ),
                    content=build_diagnostic_text(
                        snapshot
                    ).encode("utf-8"),
                )
            )

        if (
            self.config.collection
            .include_incident_snapshot
        ):
            incident_content = (
                self._build_incident_snapshot_json(
                    snapshot
                ).encode("utf-8")
            )

            artifacts.append(
                self._create_artifact(
                    artifact_type=(
                        DiagnosticArtifactType
                        .INCIDENT_SNAPSHOT
                    ),
                    file_name=(
                        self.config.files
                        .incident_snapshot_name
                    ),
                    content=incident_content,
                )
            )

        return tuple(artifacts)

    @staticmethod
    def _create_artifact(
        *,
        artifact_type: DiagnosticArtifactType,
        file_name: str,
        content: bytes,
    ) -> _DiagnosticArtifactContent:
        """Create metadata and content for one artifact."""
        record = DiagnosticArtifactRecord(
            artifact_type=artifact_type,
            file_name=file_name,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )

        return _DiagnosticArtifactContent(
            record=record,
            content=content,
        )

    def _write_archive(
        self,
        *,
        archive_path: Path,
        manifest_content: bytes,
        artifacts: tuple[
            _DiagnosticArtifactContent,
            ...,
        ],
    ) -> None:
        """Write the manifest and all artifacts into a ZIP."""
        with ZipFile(
            archive_path,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                self.config.files.manifest_name,
                manifest_content,
            )

            for artifact in artifacts:
                archive.writestr(
                    artifact.record.file_name,
                    artifact.content,
                )

    @staticmethod
    def _create_temporary_path(
        *,
        output_directory: Path,
        bundle_id: str,
    ) -> Path:
        """Create a temporary file in the output directory."""
        with NamedTemporaryFile(
            prefix=f".{bundle_id}-",
            suffix=".tmp",
            dir=output_directory,
            delete=False,
        ) as temporary_file:
            return Path(temporary_file.name)

    @staticmethod
    def _build_manifest_json(
        manifest: DiagnosticBundleManifest,
    ) -> str:
        """Serialize one diagnostic manifest."""
        payload = {
            "schema_version": manifest.schema_version,
            "bundle_id": manifest.bundle_id,
            "generated_at": (
                manifest.generated_at.isoformat()
            ),
            "host_name": manifest.host_name,
            "artifacts": [
                {
                    "artifact_type": (
                        artifact.artifact_type.value
                    ),
                    "file_name": artifact.file_name,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                }
                for artifact in manifest.artifacts
            ],
        }

        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

    @staticmethod
    def _build_incident_snapshot_json(
        snapshot: DiagnosticSnapshot,
    ) -> str:
        """Serialize incidents from one diagnostic snapshot."""
        payload = {
            "schema_version": (
                _INCIDENT_SNAPSHOT_SCHEMA_VERSION
            ),
            "generated_at": (
                snapshot.generated_at.isoformat()
            ),
            "host_name": snapshot.host_name,
            "active_count": (
                snapshot.active_incident_count
            ),
            "resolved_count": (
                snapshot.resolved_incident_count
            ),
            "records": [
                {
                    "incident_id": incident.incident_id,
                    "source_type": (
                        incident.source_type.value
                    ),
                    "source_id": incident.source_id,
                    "source_label": incident.source_label,
                    "severity": incident.severity.value,
                    "status": incident.status.value,
                    "description": incident.description,
                    "first_seen_at": (
                        incident.first_seen_at.isoformat()
                    ),
                    "last_seen_at": (
                        incident.last_seen_at.isoformat()
                    ),
                    "occurrence_count": (
                        incident.occurrence_count
                    ),
                    "resolved_at": (
                        incident.resolved_at.isoformat()
                        if incident.resolved_at is not None
                        else None
                    ),
                }
                for incident in snapshot.incidents
            ],
        }

        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )