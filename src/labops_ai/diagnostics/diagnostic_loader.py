"""Load diagnostic bundle settings from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    DIAGNOSTIC_BUNDLE_CONFIG_PATH,
    load_json_config,
)
from labops_ai.diagnostics.diagnostic_config import (
    DiagnosticBundleCollectionConfig,
    DiagnosticBundleConfig,
    DiagnosticBundleFilesConfig,
    DiagnosticBundleOutputConfig,
)


class DiagnosticBundleConfigLoader:
    """Load and validate diagnostic bundle configuration."""

    def __init__(
        self,
        config_path: str | Path = DIAGNOSTIC_BUNDLE_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> DiagnosticBundleConfig:
        """Load JSON into validated diagnostic configuration."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        return DiagnosticBundleConfig(
            output=DiagnosticBundleOutputConfig(
                **configuration["output"]
            ),
            collection=DiagnosticBundleCollectionConfig(
                **configuration["collection"]
            ),
            files=DiagnosticBundleFilesConfig(
                **configuration["files"]
            ),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate all required sections and keys."""
        cls._validate_exact_keys(
            configuration,
            {"output", "collection", "files"},
            "configuration",
        )

        output = cls._require_object(
            configuration,
            "output",
        )
        collection = cls._require_object(
            configuration,
            "collection",
        )
        files = cls._require_object(
            configuration,
            "files",
        )

        cls._validate_exact_keys(
            output,
            {
                "directory",
                "archive_prefix",
                "timestamp_format",
            },
            "output section",
        )
        cls._validate_exact_keys(
            collection,
            {
                "include_json_report",
                "include_text_report",
                "include_incident_snapshot",
            },
            "collection section",
        )
        cls._validate_exact_keys(
            files,
            {
                "manifest_name",
                "json_report_name",
                "text_report_name",
                "incident_snapshot_name",
            },
            "files section",
        )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return one required JSON object section."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Diagnostic bundle section '{section_name}' "
                "must be a JSON object."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported configuration keys."""
        configuration_keys = set(configuration)
        missing_keys = required_keys - configuration_keys
        unexpected_keys = configuration_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise ValueError(
                f"Missing required keys in diagnostic bundle "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(
                sorted(unexpected_keys)
            )
            raise ValueError(
                f"Unsupported keys in diagnostic bundle "
                f"{location}: {formatted_keys}."
            )