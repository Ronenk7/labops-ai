"""Shared utilities for loading external JSON configuration files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIRECTORY = PROJECT_ROOT / "config"

SYSTEM_HEALTH_CONFIG_PATH = CONFIG_DIRECTORY / "system_health.json"
NETWORK_CONNECTIVITY_CONFIG_PATH = CONFIG_DIRECTORY / "network_connectivity.json"
SERVICE_MONITOR_CONFIG_PATH = CONFIG_DIRECTORY / "service_monitor.json"
PROCESS_MONITOR_CONFIG_PATH = CONFIG_DIRECTORY / "process_monitor.json"
LOG_ANALYZER_CONFIG_PATH = CONFIG_DIRECTORY / "log_analyzer.json"
INCIDENT_MANAGEMENT_CONFIG_PATH = CONFIG_DIRECTORY / "incident_management.json"
INCIDENT_SIGNALS_CONFIG_PATH = CONFIG_DIRECTORY / "incident_signals.json"
DIAGNOSTIC_BUNDLE_CONFIG_PATH = CONFIG_DIRECTORY / "diagnostic_bundle.json"
RUN_HISTORY_CONFIG_PATH = CONFIG_DIRECTORY / "run_history.json"


def load_json_config(config_path: str | Path) -> dict[str, Any]:
    """
    Read and parse an external JSON configuration file.

    Args:
        config_path:
            Path to the JSON configuration file.

    Returns:
        The parsed JSON object as a dictionary.

    Raises:
        FileNotFoundError:
            If the configuration file does not exist.

        IsADirectoryError:
            If the supplied path points to a directory.

        ValueError:
            If the file contains invalid JSON or the JSON root
            is not an object.
    """
    path = Path(config_path)

    try:
        raw_content = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Configuration file was not found: {path}"
        ) from error
    except IsADirectoryError as error:
        raise IsADirectoryError(
            f"Configuration path points to a directory: {path}"
        ) from error

    try:
        configuration = json.loads(raw_content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Configuration file contains invalid JSON: {path}"
        ) from error

    if not isinstance(configuration, dict):
        raise ValueError(
            "Configuration file must contain a JSON object."
        )

    return configuration