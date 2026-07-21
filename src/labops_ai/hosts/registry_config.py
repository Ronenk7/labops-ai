"""Validated configuration for the host registry."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from labops_ai.hosts.status import (
    HostAvailabilityPolicy,
)


_ALLOWED_DATABASE_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
}
_MAX_BUSY_TIMEOUT_SECONDS = 300.0


def _normalize_database_path(value: object) -> str:
    """Validate and normalize the registry database path."""
    if not isinstance(value, str):
        raise TypeError(
            "Host registry database path must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "Host registry database path must not be empty."
        )

    suffix = Path(normalized).suffix.casefold()

    if suffix not in _ALLOWED_DATABASE_SUFFIXES:
        allowed = ", ".join(
            sorted(_ALLOWED_DATABASE_SUFFIXES)
        )
        raise ValueError(
            "Host registry database path must use one of "
            f"these suffixes: {allowed}."
        )

    return normalized


def _normalize_busy_timeout(value: object) -> float:
    """Validate the SQLite busy timeout."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise TypeError(
            "Host registry busy timeout must be numeric."
        )

    normalized = float(value)

    if not isfinite(normalized):
        raise ValueError(
            "Host registry busy timeout must be finite."
        )

    if normalized <= 0:
        raise ValueError(
            "Host registry busy timeout must be positive."
        )

    if normalized > _MAX_BUSY_TIMEOUT_SECONDS:
        raise ValueError(
            "Host registry busy timeout must not exceed "
            f"{_MAX_BUSY_TIMEOUT_SECONDS} seconds."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class HostRegistryStorageConfig:
    """Represent host-registry SQLite settings."""

    database_path: str
    busy_timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate and normalize storage settings."""
        object.__setattr__(
            self,
            "database_path",
            _normalize_database_path(
                self.database_path
            ),
        )
        object.__setattr__(
            self,
            "busy_timeout_seconds",
            _normalize_busy_timeout(
                self.busy_timeout_seconds
            ),
        )


@dataclass(frozen=True, slots=True)
class HostRegistryConfig:
    """Group host storage and availability settings."""

    storage: HostRegistryStorageConfig
    availability: HostAvailabilityPolicy

    def __post_init__(self) -> None:
        """Validate complete registry configuration."""
        if not isinstance(
            self.storage,
            HostRegistryStorageConfig,
        ):
            raise TypeError(
                "storage must be a "
                "HostRegistryStorageConfig instance."
            )

        if not isinstance(
            self.availability,
            HostAvailabilityPolicy,
        ):
            raise TypeError(
                "availability must be a "
                "HostAvailabilityPolicy instance."
            )
