"""Shared utilities for external JSON configuration files."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


_PROFILE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]+$"
)


def _resolve_project_root() -> Path:
    """Resolve the runtime project root."""
    configured_root = os.environ.get(
        "LABOPS_AI_PROJECT_ROOT"
    )

    if configured_root:
        candidate = Path(
            configured_root
        ).expanduser()

        if not candidate.is_absolute():
            candidate = (
                Path.cwd() / candidate
            )

        return candidate.resolve()

    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = _resolve_project_root()
CONFIG_DIRECTORY = PROJECT_ROOT / "config"


def _resolve_config_path(
    file_name: str,
) -> Path:
    """Resolve a profile override or the default config."""
    if not isinstance(file_name, str):
        raise TypeError(
            "Configuration file name must be a string."
        )

    normalized_file_name = file_name.strip()

    if not normalized_file_name:
        raise ValueError(
            "Configuration file name must not be empty."
        )

    default_path = (
        CONFIG_DIRECTORY / normalized_file_name
    )

    raw_profile = os.environ.get(
        "LABOPS_AI_MONITORING_PROFILE"
    )

    if raw_profile is None:
        return default_path

    profile_name = raw_profile.strip()

    if not profile_name:
        return default_path

    if not _PROFILE_NAME_PATTERN.fullmatch(
        profile_name
    ):
        raise ValueError(
            "LABOPS_AI_MONITORING_PROFILE contains "
            "unsupported characters."
        )

    profile_path = (
        CONFIG_DIRECTORY
        / "profiles"
        / profile_name
        / normalized_file_name
    )

    if profile_path.is_file():
        return profile_path

    return default_path


SYSTEM_HEALTH_CONFIG_PATH = _resolve_config_path(
    "system_health.json"
)
NETWORK_CONNECTIVITY_CONFIG_PATH = _resolve_config_path(
    "network_connectivity.json"
)
SERVICE_MONITOR_CONFIG_PATH = _resolve_config_path(
    "service_monitor.json"
)
PROCESS_MONITOR_CONFIG_PATH = _resolve_config_path(
    "process_monitor.json"
)
LOG_ANALYZER_CONFIG_PATH = _resolve_config_path(
    "log_analyzer.json"
)
INCIDENT_MANAGEMENT_CONFIG_PATH = _resolve_config_path(
    "incident_management.json"
)
INCIDENT_SIGNALS_CONFIG_PATH = _resolve_config_path(
    "incident_signals.json"
)
DIAGNOSTIC_BUNDLE_CONFIG_PATH = _resolve_config_path(
    "diagnostic_bundle.json"
)
RUN_HISTORY_CONFIG_PATH = _resolve_config_path(
    "run_history.json"
)
RECOVERY_ACTIONS_CONFIG_PATH = _resolve_config_path(
    "recovery_actions.json"
)
API_SERVER_CONFIG_PATH = _resolve_config_path(
    "api_server.json"
)
HOST_REGISTRY_CONFIG_PATH = _resolve_config_path(
    "host_registry.json"
)
HOST_AGENT_CONFIG_PATH = _resolve_config_path(
    "host_agent.json"
)


def load_json_config(
    config_path: str | Path,
) -> dict[str, Any]:
    """Read and parse one external JSON object."""
    path = Path(config_path)

    try:
        raw_content = path.read_text(
            encoding="utf-8"
        )
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Configuration file was not found: {path}"
        ) from error
    except IsADirectoryError as error:
        raise IsADirectoryError(
            "Configuration path points to "
            f"a directory: {path}"
        ) from error

    try:
        configuration = json.loads(
            raw_content
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "Configuration file contains "
            f"invalid JSON: {path}"
        ) from error

    if not isinstance(configuration, dict):
        raise ValueError(
            "Configuration file must contain "
            "a JSON object."
        )

    return configuration
