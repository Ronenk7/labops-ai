"""Load system health settings from an external JSON configuration file."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from labops_ai.config.system_health_config import (
    SUPPORTED_SYSTEM_METRICS,
    HealthThresholds,
    SystemHealthCollectionConfig,
    SystemHealthConfig,
    SystemHealthReportConfig,
)
from labops_ai.config.utils import SYSTEM_HEALTH_CONFIG_PATH, load_json_config


class SystemHealthConfigLoader:
    """Load and validate system health configuration from JSON."""

    def __init__(self, config_path: str | Path = SYSTEM_HEALTH_CONFIG_PATH) -> None:
        """Initialize the loader with a configuration file path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configuration file path used by the loader."""
        return self._config_path

    def load(self) -> SystemHealthConfig:
        """Load, validate, and convert the system health configuration."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        collection = configuration["collection"]
        metrics = configuration["metrics"]
        report = configuration["report"]
        metric_labels = report["metric_labels"]

        metric_thresholds = {
            metric_name: HealthThresholds(
                warning=metric_values["warning"],
                critical=metric_values["critical"],
            )
            for metric_name, metric_values in metrics.items()
        }

        return SystemHealthConfig(
            collection=SystemHealthCollectionConfig(
                cpu_sample_interval_seconds=collection["cpu_sample_interval_seconds"],
                disk_mount_point=collection["disk_mount_point"],
            ),
            metric_thresholds=metric_thresholds,
            report=SystemHealthReportConfig(
                title=report["title"],
                separator=report["separator"],
                overall_label=report["overall_label"],
                metric_labels=metric_labels,
            ),
        )

    @classmethod
    def _validate_configuration(cls, configuration: dict[str, Any]) -> None:
        """Validate all required sections and fields in the JSON structure."""
        cls._validate_exact_keys(
            configuration,
            {"collection", "metrics", "report"},
            "configuration",
        )

        collection = cls._require_section(configuration, "collection")
        metrics = cls._require_section(configuration, "metrics")
        report = cls._require_section(configuration, "report")

        cls._validate_exact_keys(
            collection,
            {"cpu_sample_interval_seconds", "disk_mount_point"},
            "collection section",
        )
        cls._validate_exact_keys(
            metrics,
            set(SUPPORTED_SYSTEM_METRICS),
            "metrics section",
        )
        cls._validate_exact_keys(
            report,
            {"title", "separator", "overall_label", "metric_labels"},
            "report section",
        )

        for metric_name in metrics:
            metric_values = cls._require_section(metrics, metric_name)
            cls._validate_exact_keys(
                metric_values,
                {"warning", "critical"},
                f"metric '{metric_name}'",
            )

        metric_labels = cls._require_section(report, "metric_labels")
        cls._validate_exact_keys(
            metric_labels,
            set(SUPPORTED_SYSTEM_METRICS),
            "report metric_labels section",
        )

    @staticmethod
    def _require_section(
        configuration: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return a required JSON object section."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"System health section '{section_name}' must be a JSON object."
            )

        return section

    @staticmethod
    def _validate_exact_keys(
        configuration: dict[str, Any],
        required_keys: set[str],
        location: str,
    ) -> None:
        """Reject missing and unsupported JSON keys."""
        configuration_keys = set(configuration)
        missing_keys = required_keys - configuration_keys
        unexpected_keys = configuration_keys - required_keys

        if missing_keys:
            formatted_keys = ", ".join(sorted(missing_keys))
            raise ValueError(
                f"Missing required keys in system health {location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                f"Unsupported keys in system health {location}: {formatted_keys}."
            )