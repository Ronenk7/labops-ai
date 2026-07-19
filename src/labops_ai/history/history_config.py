"""Validated configuration models for run history storage."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path


_ALLOWED_DATABASE_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
}
_MAX_BUSY_TIMEOUT_SECONDS = 300.0
_MAX_RETENTION_RUNS = 1_000_000
_MAX_RETENTION_DAYS = 3_650


def _normalize_non_empty_string(
    field_name: str,
    value: object,
) -> str:
    """Validate and normalize one required string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


def _normalize_database_path(value: object) -> str:
    """Validate and normalize the SQLite database path."""
    normalized_value = _normalize_non_empty_string(
        "Run history database path",
        value,
    )
    suffix = Path(normalized_value).suffix.casefold()

    if suffix not in _ALLOWED_DATABASE_SUFFIXES:
        allowed_suffixes = ", ".join(
            sorted(_ALLOWED_DATABASE_SUFFIXES)
        )
        raise ValueError(
            "Run history database path must use one of "
            f"these suffixes: {allowed_suffixes}."
        )

    return normalized_value


def _normalize_busy_timeout(value: object) -> float:
    """Validate and normalize the SQLite busy timeout."""
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            "Run history busy timeout must be numeric."
        )

    normalized_value = float(value)

    if not isfinite(normalized_value):
        raise ValueError(
            "Run history busy timeout must be finite."
        )

    if normalized_value <= 0.0:
        raise ValueError(
            "Run history busy timeout must be greater than zero."
        )

    if normalized_value > _MAX_BUSY_TIMEOUT_SECONDS:
        raise ValueError(
            "Run history busy timeout must not exceed "
            f"{_MAX_BUSY_TIMEOUT_SECONDS} seconds."
        )

    return normalized_value


def _normalize_positive_integer(
    field_name: str,
    value: object,
    *,
    maximum: int,
) -> int:
    """Validate a bounded positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    if value > maximum:
        raise ValueError(
            f"{field_name} must not exceed {maximum}."
        )

    return value


@dataclass(frozen=True, slots=True)
class RunHistoryStorageConfig:
    """Represent SQLite database storage settings."""

    database_path: str
    busy_timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate and normalize SQLite storage settings."""
        database_path = _normalize_database_path(
            self.database_path
        )
        busy_timeout_seconds = _normalize_busy_timeout(
            self.busy_timeout_seconds
        )

        object.__setattr__(
            self,
            "database_path",
            database_path,
        )
        object.__setattr__(
            self,
            "busy_timeout_seconds",
            busy_timeout_seconds,
        )


@dataclass(frozen=True, slots=True)
class RunHistoryRetentionConfig:
    """Represent automatic history retention settings."""

    max_runs: int
    max_age_days: int | None
    prune_on_write: bool

    def __post_init__(self) -> None:
        """Validate all retention settings."""
        max_runs = _normalize_positive_integer(
            "Run history maximum run count",
            self.max_runs,
            maximum=_MAX_RETENTION_RUNS,
        )

        max_age_days = None
        if self.max_age_days is not None:
            max_age_days = _normalize_positive_integer(
                "Run history maximum age",
                self.max_age_days,
                maximum=_MAX_RETENTION_DAYS,
            )

        if not isinstance(self.prune_on_write, bool):
            raise TypeError(
                "Run history prune_on_write must be a boolean."
            )

        object.__setattr__(
            self,
            "max_runs",
            max_runs,
        )
        object.__setattr__(
            self,
            "max_age_days",
            max_age_days,
        )


@dataclass(frozen=True, slots=True)
class RunHistoryConfig:
    """Group all run history configuration."""

    storage: RunHistoryStorageConfig
    retention: RunHistoryRetentionConfig

    def __post_init__(self) -> None:
        """Validate the complete run history configuration."""
        if not isinstance(
            self.storage,
            RunHistoryStorageConfig,
        ):
            raise TypeError(
                "storage must be a "
                "RunHistoryStorageConfig instance."
            )

        if not isinstance(
            self.retention,
            RunHistoryRetentionConfig,
        ):
            raise TypeError(
                "retention must be a "
                "RunHistoryRetentionConfig instance."
            )
