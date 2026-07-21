"""Load process monitoring settings from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    PROCESS_MONITOR_CONFIG_PATH,
    load_json_config,
)
from labops_ai.processes.process_config import (
    ProcessCollectionConfig,
    ProcessCpuThresholds,
    ProcessMemoryThresholds,
    ProcessMonitorConfig,
    ProcessReportConfig,
    ProcessTargetConfig,
)


class ProcessMonitorConfigLoader:
    """Load and validate process monitor configuration."""

    def __init__(
        self,
        config_path: str | Path = PROCESS_MONITOR_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a configuration path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> ProcessMonitorConfig:
        """Load external JSON into validated process models."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        collection_values = configuration["collection"]
        process_values = configuration["processes"]
        report_values = configuration["report"]

        processes = tuple(
            ProcessTargetConfig(
                process_name=process["process_name"],
                label=process["label"],
                required=process["required"],
                enabled=process.get("enabled", True),
                cpu_thresholds_percent=ProcessCpuThresholds(
                    warning=process[
                        "cpu_thresholds_percent"
                    ]["warning"],
                    critical=process[
                        "cpu_thresholds_percent"
                    ]["critical"],
                ),
                memory_thresholds_mb=ProcessMemoryThresholds(
                    warning=process[
                        "memory_thresholds_mb"
                    ]["warning"],
                    critical=process[
                        "memory_thresholds_mb"
                    ]["critical"],
                ),
            )
            for process in process_values
        )

        return ProcessMonitorConfig(
            collection=ProcessCollectionConfig(
                cpu_sample_interval_seconds=collection_values[
                    "cpu_sample_interval_seconds"
                ],
            ),
            processes=processes,
            report=ProcessReportConfig(**report_values),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate required JSON sections and exact keys."""
        cls._validate_exact_keys(
            configuration,
            {"collection", "processes", "report"},
            "configuration",
        )

        collection = cls._require_object(
            configuration,
            "collection",
            "configuration",
        )
        processes = cls._require_list(
            configuration,
            "processes",
            "configuration",
        )
        report = cls._require_object(
            configuration,
            "report",
            "configuration",
        )

        cls._validate_exact_keys(
            collection,
            {"cpu_sample_interval_seconds"},
            "collection section",
        )

        cls._validate_exact_keys(
            report,
            {
                "title",
                "separator",
                "overall_label",
                "process_label",
                "name_label",
                "required_label",
                "check_status_label",
                "health_label",
                "instances_label",
                "pids_label",
                "cpu_label",
                "memory_label",
                "runtime_label",
                "failure_reason_label",
                "error_message_label",
                "yes_value",
                "no_value",
                "cpu_unit",
                "memory_unit",
                "runtime_unit",
                "decimal_places",
            },
            "report section",
        )

        if not processes:
            raise ValueError(
                "Process monitor processes section must not be empty."
            )

        for index, process in enumerate(processes):
            if not isinstance(process, dict):
                raise ValueError(
                    f"Process entry {index} must be a JSON object."
                )

            enabled = process.get(
                "enabled",
                True,
            )

            if not isinstance(enabled, bool):
                raise ValueError(
                    f"Process entry {index} enabled "
                    "setting must be a boolean."
                )

            required_process = {
                key: value
                for key, value in process.items()
                if key != "enabled"
            }

            cls._validate_exact_keys(
                required_process,
                {
                    "process_name",
                    "label",
                    "required",
                    "cpu_thresholds_percent",
                    "memory_thresholds_mb",
                },
                f"process entry {index}",
            )

            cpu_thresholds = cls._require_object(
                process,
                "cpu_thresholds_percent",
                f"process entry {index}",
            )
            memory_thresholds = cls._require_object(
                process,
                "memory_thresholds_mb",
                f"process entry {index}",
            )

            cls._validate_exact_keys(
                cpu_thresholds,
                {"warning", "critical"},
                f"process entry {index} CPU thresholds",
            )
            cls._validate_exact_keys(
                memory_thresholds,
                {"warning", "critical"},
                f"process entry {index} memory thresholds",
            )

    @staticmethod
    def _require_object(
        configuration: dict[str, Any],
        section_name: str,
        location: str,
    ) -> dict[str, Any]:
        """Return a required JSON object."""
        section = configuration[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Process monitor {location} '{section_name}' "
                "must be a JSON object."
            )

        return section

    @staticmethod
    def _require_list(
        configuration: dict[str, Any],
        section_name: str,
        location: str,
    ) -> list[Any]:
        """Return a required JSON array."""
        section = configuration[section_name]

        if not isinstance(section, list):
            raise ValueError(
                f"Process monitor {location} '{section_name}' "
                "must be a JSON array."
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
                f"Missing required keys in process monitor "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                f"Unsupported keys in process monitor "
                f"{location}: {formatted_keys}."
            )