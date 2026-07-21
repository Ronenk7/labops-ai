"""Read complete monitoring details from diagnostic ZIP archives."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, LargeZipFile, ZipFile

from labops_ai.api.schemas import (
    RunDetailsResponse,
)
from labops_ai.api.service import RunHistoryApiService
from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.diagnostics import DiagnosticBundleConfig


_MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024
_MAX_REPORT_SIZE_BYTES = 10 * 1024 * 1024

_REQUIRED_REPORT_KEYS = {
    "schema_version",
    "generated_at",
    "host_name",
    "overall_status",
    "summary",
    "system",
    "network",
    "services",
    "processes",
    "logs",
    "incidents",
}


class DiagnosticArchiveError(RuntimeError):
    """Represent an unavailable or invalid diagnostic archive."""


@dataclass(frozen=True, slots=True)
class DiagnosticArchiveReader:
    """Read and validate one JSON report inside a ZIP bundle."""

    config: DiagnosticBundleConfig

    def __post_init__(self) -> None:
        """Validate the diagnostic bundle configuration."""
        if not isinstance(
            self.config,
            DiagnosticBundleConfig,
        ):
            raise TypeError(
                "config must be a DiagnosticBundleConfig."
            )

    def read(
        self,
        archive_path: str | Path,
    ) -> dict[str, Any]:
        """Return the real diagnostic JSON stored in a ZIP."""
        resolved_path = self._resolve_archive_path(
            archive_path
        )

        try:
            archive_size = resolved_path.stat().st_size
        except OSError as error:
            raise DiagnosticArchiveError(
                "Diagnostic archive metadata "
                "could not be read."
            ) from error

        if archive_size > _MAX_ARCHIVE_SIZE_BYTES:
            raise DiagnosticArchiveError(
                "Diagnostic archive exceeds "
                "the supported size."
            )

        try:
            with ZipFile(resolved_path, mode="r") as archive:
                payload = self._read_json_report(archive)
        except (
            OSError,
            BadZipFile,
            LargeZipFile,
            RuntimeError,
        ) as error:
            raise DiagnosticArchiveError(
                "Diagnostic archive could not be read."
            ) from error

        self._validate_payload(payload)
        return payload

    def resolve_archive_path(
        self,
        archive_path: str | Path,
    ) -> Path:
        """Return one validated diagnostic archive path."""
        return self._resolve_archive_path(archive_path)

    def _resolve_archive_path(
        self,
        archive_path: str | Path,
    ) -> Path:
        """Resolve and restrict the archive to the bundle directory."""
        try:
            candidate = Path(archive_path).expanduser()
        except TypeError as error:
            raise TypeError(
                "archive_path must be path-compatible."
            ) from error

        if candidate.suffix.casefold() != ".zip":
            raise DiagnosticArchiveError(
                "Diagnostic archive must use a .zip suffix."
            )

        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

        try:
            resolved_path = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise DiagnosticArchiveError(
                "Diagnostic archive was not found."
            ) from error
        except OSError as error:
            raise DiagnosticArchiveError(
                "Diagnostic archive path "
                "could not be resolved."
            ) from error

        output_directory = Path(
            self.config.output.directory
        ).expanduser()

        if not output_directory.is_absolute():
            output_directory = (
                PROJECT_ROOT / output_directory
            )

        try:
            allowed_directory = (
                output_directory.resolve(strict=True)
            )
            resolved_path.relative_to(allowed_directory)
        except (FileNotFoundError, OSError, ValueError) as error:
            raise DiagnosticArchiveError(
                "Diagnostic archive is outside "
                "the configured bundle directory."
            ) from error

        return resolved_path

    def _read_json_report(
        self,
        archive: ZipFile,
    ) -> dict[str, Any]:
        """Read the configured JSON report without extracting it."""
        report_name = self.config.files.json_report_name

        try:
            report_info = archive.getinfo(report_name)
        except KeyError as error:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report "
                "is missing from the archive."
            ) from error

        if report_info.is_dir():
            raise DiagnosticArchiveError(
                "Diagnostic JSON report is not a file."
            )

        if report_info.flag_bits & 0x1:
            raise DiagnosticArchiveError(
                "Encrypted diagnostic reports "
                "are not supported."
            )

        if report_info.file_size > _MAX_REPORT_SIZE_BYTES:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report exceeds "
                "the supported size."
            )

        try:
            raw_content = archive.read(report_info)
        except (OSError, RuntimeError) as error:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report "
                "could not be read."
            ) from error

        if len(raw_content) > _MAX_REPORT_SIZE_BYTES:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report exceeds "
                "the supported size."
            )

        try:
            decoded_content = raw_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report is not UTF-8."
            ) from error

        try:
            payload = json.loads(decoded_content)
        except json.JSONDecodeError as error:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report is invalid."
            ) from error

        if not isinstance(payload, dict):
            raise DiagnosticArchiveError(
                "Diagnostic JSON report root "
                "must be an object."
            )

        return payload

    @staticmethod
    def _validate_payload(
        payload: dict[str, Any],
    ) -> None:
        """Validate the minimum supported report structure."""
        missing_keys = _REQUIRED_REPORT_KEYS - set(payload)

        if missing_keys:
            raise DiagnosticArchiveError(
                "Diagnostic JSON report is missing: "
                + ", ".join(sorted(missing_keys))
            )

        schema_version = payload["schema_version"]

        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != 1
        ):
            raise DiagnosticArchiveError(
                "Diagnostic JSON report schema "
                "is unsupported."
            )

        for section_name in (
            "summary",
            "system",
            "network",
            "services",
            "processes",
            "logs",
            "incidents",
        ):
            if not isinstance(
                payload[section_name],
                dict,
            ):
                raise DiagnosticArchiveError(
                    f"Diagnostic section "
                    f"'{section_name}' is invalid."
                )


@dataclass(frozen=True, slots=True)
class RunDetailsApiService:
    """Combine run history metadata with its real ZIP report."""

    history_service: RunHistoryApiService
    archive_reader: DiagnosticArchiveReader

    def __post_init__(self) -> None:
        """Validate dependencies."""
        if not isinstance(
            self.history_service,
            RunHistoryApiService,
        ):
            raise TypeError(
                "history_service must be "
                "a RunHistoryApiService."
            )

        if not isinstance(
            self.archive_reader,
            DiagnosticArchiveReader,
        ):
            raise TypeError(
                "archive_reader must be "
                "a DiagnosticArchiveReader."
            )

    def get_by_id(
        self,
        run_id: int,
    ) -> RunDetailsResponse | None:
        """Return one run and its complete archived diagnostics."""
        run = self.history_service.get_by_id(run_id)

        if run is None:
            return None

        diagnostics = self.archive_reader.read(
            run.archive_path
        )

        report_host = diagnostics.get("host_name")

        if (
            not isinstance(report_host, str)
            or report_host.casefold()
            != run.host_name.casefold()
        ):
            raise DiagnosticArchiveError(
                "Diagnostic report host does not match "
                "the selected monitoring run."
            )

        return RunDetailsResponse(
            run=run,
            diagnostics=diagnostics,
        )

    def get_archive_path(
        self,
        run_id: int,
    ) -> Path | None:
        """Return the validated ZIP path for one run."""
        run = self.history_service.get_by_id(run_id)

        if run is None:
            return None

        return self.archive_reader.resolve_archive_path(
            run.archive_path
        )
