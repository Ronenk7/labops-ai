"""Load log analysis settings from external JSON."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    LOG_ANALYZER_CONFIG_PATH,
    load_json_config,
)
from labops_ai.health_status import HealthStatus
from labops_ai.logs.log_config import (
    LogAnalyzerConfig,
    LogCollectionConfig,
    LogReportConfig,
    LogRuleConfig,
    LogSourceConfig,
)


class LogAnalyzerConfigLoader:
    """Load and validate external log analyzer configuration."""

    def __init__(
        self,
        config_path: str | Path = LOG_ANALYZER_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a configuration path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configured JSON path."""
        return self._config_path

    def load(self) -> LogAnalyzerConfig:
        """Load external JSON into validated log models."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        collection_values = configuration["collection"]
        source_values = configuration["sources"]
        rule_values = configuration["rules"]
        report_values = configuration["report"]

        sources = tuple(
            LogSourceConfig(
                source_id=source["source_id"],
                label=source["label"],
                path=source["path"],
                required=source["required"],
            )
            for source in source_values
        )

        rules = tuple(
            LogRuleConfig(
                rule_id=rule["rule_id"],
                label=rule["label"],
                pattern=rule["pattern"],
                severity=HealthStatus(rule["severity"]),
                case_sensitive=rule["case_sensitive"],
            )
            for rule in rule_values
        )

        return LogAnalyzerConfig(
            collection=LogCollectionConfig(
                encoding=collection_values["encoding"],
                max_lines_per_source=collection_values[
                    "max_lines_per_source"
                ],
            ),
            sources=sources,
            rules=rules,
            report=LogReportConfig(**report_values),
        )

    @classmethod
    def _validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate required JSON sections and exact keys."""
        cls._validate_exact_keys(
            configuration,
            {"collection", "sources", "rules", "report"},
            "configuration",
        )

        collection = cls._require_object(
            configuration,
            "collection",
            "configuration",
        )
        sources = cls._require_list(
            configuration,
            "sources",
            "configuration",
        )
        rules = cls._require_list(
            configuration,
            "rules",
            "configuration",
        )
        report = cls._require_object(
            configuration,
            "report",
            "configuration",
        )

        cls._validate_exact_keys(
            collection,
            {"encoding", "max_lines_per_source"},
            "collection section",
        )

        cls._validate_exact_keys(
            report,
            {
                "title",
                "separator",
                "overall_label",
                "source_label",
                "source_id_label",
                "path_label",
                "required_label",
                "scan_status_label",
                "health_label",
                "lines_scanned_label",
                "matches_label",
                "match_label",
                "rule_label",
                "severity_label",
                "line_number_label",
                "content_label",
                "failure_reason_label",
                "error_message_label",
                "yes_value",
                "no_value",
            },
            "report section",
        )

        if not sources:
            raise ValueError(
                "Log analyzer sources section must not be empty."
            )

        if not rules:
            raise ValueError(
                "Log analyzer rules section must not be empty."
            )

        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ValueError(
                    f"Log source entry {index} must be a JSON object."
                )

            cls._validate_exact_keys(
                source,
                {"source_id", "label", "path", "required"},
                f"source entry {index}",
            )

        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValueError(
                    f"Log rule entry {index} must be a JSON object."
                )

            cls._validate_exact_keys(
                rule,
                {
                    "rule_id",
                    "label",
                    "pattern",
                    "severity",
                    "case_sensitive",
                },
                f"rule entry {index}",
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
                f"Log analyzer {location} '{section_name}' "
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
                f"Log analyzer {location} '{section_name}' "
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
                f"Missing required keys in log analyzer "
                f"{location}: {formatted_keys}."
            )

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(
                f"Unsupported keys in log analyzer "
                f"{location}: {formatted_keys}."
            )