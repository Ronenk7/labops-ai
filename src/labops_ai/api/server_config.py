"""Configuration for the production LabOps AI API server."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from labops_ai.config.utils import (
    API_SERVER_CONFIG_PATH,
    load_json_config,
)


_LOG_LEVELS = {
    "critical",
    "error",
    "warning",
    "info",
    "debug",
    "trace",
}


@dataclass(frozen=True, slots=True)
class ApiServerConfig:
    """Represent validated Uvicorn server settings."""

    host: str
    port: int
    log_level: str
    access_log: bool
    proxy_headers: bool
    workers: int

    def __post_init__(self) -> None:
        """Validate all API server settings."""
        if not isinstance(self.host, str):
            raise TypeError(
                "API server host must be a string."
            )

        host = self.host.strip()

        if not host:
            raise ValueError(
                "API server host must not be empty."
            )

        if (
            isinstance(self.port, bool)
            or not isinstance(self.port, int)
        ):
            raise TypeError(
                "API server port must be an integer."
            )

        if not 1 <= self.port <= 65535:
            raise ValueError(
                "API server port must be between "
                "1 and 65535."
            )

        if not isinstance(self.log_level, str):
            raise TypeError(
                "API server log level must be a string."
            )

        log_level = self.log_level.strip().casefold()

        if log_level not in _LOG_LEVELS:
            raise ValueError(
                "Unsupported API server log level."
            )

        for field_name in (
            "access_log",
            "proxy_headers",
        ):
            if not isinstance(
                getattr(self, field_name),
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a Boolean."
                )

        if (
            isinstance(self.workers, bool)
            or not isinstance(self.workers, int)
        ):
            raise TypeError(
                "API server workers must be an integer."
            )

        if not 1 <= self.workers <= 8:
            raise ValueError(
                "API server workers must be between 1 and 8."
            )

        object.__setattr__(self, "host", host)
        object.__setattr__(
            self,
            "log_level",
            log_level,
        )


class ApiServerConfigLoader:
    """Load API server settings from external JSON."""

    def __init__(
        self,
        config_path: str | Path = API_SERVER_CONFIG_PATH,
    ) -> None:
        """Initialize the loader with a JSON path."""
        self._config_path = Path(config_path)

    def load(self) -> ApiServerConfig:
        """Load and validate the complete configuration."""
        configuration = load_json_config(
            self._config_path
        )

        required_keys = {
            "host",
            "port",
            "log_level",
            "access_log",
            "proxy_headers",
            "workers",
        }
        actual_keys = set(configuration)
        missing = required_keys - actual_keys
        unexpected = actual_keys - required_keys

        if missing:
            raise ValueError(
                "Missing API server keys: "
                + ", ".join(sorted(missing))
            )

        if unexpected:
            raise ValueError(
                "Unsupported API server keys: "
                + ", ".join(sorted(unexpected))
            )

        return ApiServerConfig(
            **configuration
        )
