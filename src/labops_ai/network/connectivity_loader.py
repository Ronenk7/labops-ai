"""Load network connectivity settings from an external JSON configuration file."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from labops_ai.config.utils import NETWORK_CONNECTIVITY_CONFIG_PATH, load_json_config
from labops_ai.network.connectivity_config import (ConnectionSettings, ConnectivityConfig, DnsTestConfig, LatencyThresholds, TcpTestConfig)


class ConnectivityConfigLoader:
    """Load and validate network connectivity configuration from JSON."""

    def __init__(self, config_path: str | Path = NETWORK_CONNECTIVITY_CONFIG_PATH) -> None:
        """Initialize the loader with a configuration file path."""
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the configuration file path used by the loader."""
        return self._config_path

    def load(self) -> ConnectivityConfig:
        """Load, validate, and convert the connectivity configuration."""
        configuration = load_json_config(self._config_path)
        self._validate_configuration(configuration)

        dns_test = configuration["dns_test"]
        tcp_test = configuration["tcp_test"]
        connection = configuration["connection"]
        latency_thresholds = configuration["latency_thresholds_ms"]

        return ConnectivityConfig(
            dns_test=DnsTestConfig(hostname=dns_test["hostname"]),
            tcp_test=TcpTestConfig(
                host=tcp_test["host"],
                port=tcp_test["port"],
            ),
            connection=ConnectionSettings(
                timeout_seconds=connection["timeout_seconds"],
            ),
            latency_thresholds_ms=LatencyThresholds(
                warning=latency_thresholds["warning"],
                critical=latency_thresholds["critical"],
            ),
        )

    @classmethod
    def _validate_configuration(cls, configuration: dict[str, Any]) -> None:
        """Validate all required sections and fields in the JSON structure."""
        required_fields = {
            "dns_test": {"hostname"},
            "tcp_test": {"host", "port"},
            "connection": {"timeout_seconds"},
            "latency_thresholds_ms": {"warning", "critical"},
        }

        cls._validate_exact_keys(configuration, set(required_fields),"configuration")

        for section_name, section_fields in required_fields.items():
            section = configuration[section_name]

            if not isinstance(section, dict):
                raise ValueError(f"Connectivity section '{section_name}' must be a JSON object.")

            cls._validate_exact_keys(section, section_fields, f"section '{section_name}'")

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
            raise ValueError(f"Missing required keys in connectivity {location}: {formatted_keys}.")

        if unexpected_keys:
            formatted_keys = ", ".join(sorted(unexpected_keys))
            raise ValueError(f"Unsupported keys in connectivity {location}: {formatted_keys}.")