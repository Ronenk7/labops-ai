"""Validated configuration for the remote host agent."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from urllib.parse import urlparse


_MAX_TIMEOUT_SECONDS = 300.0
_MAX_INTERVAL_SECONDS = 86_400.0
_MAX_RETRY_ATTEMPTS = 10
_MAX_BACKOFF_SECONDS = 300.0


def _normalize_optional_text(
    value: object,
    field_name: str,
) -> str | None:
    """Normalize optional non-empty text."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or null."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return normalized


def _normalize_required_text(
    value: object,
    field_name: str,
) -> str:
    """Normalize required non-empty text."""
    normalized = _normalize_optional_text(
        value,
        field_name,
    )

    if normalized is None:
        raise TypeError(
            f"{field_name} must be a string."
        )

    return normalized


def _normalize_number(
    value: object,
    field_name: str,
    *,
    maximum: float,
    allow_zero: bool = False,
) -> float:
    """Validate one finite numeric setting."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise TypeError(
            f"{field_name} must be numeric."
        )

    normalized = float(value)

    if not isfinite(normalized):
        raise ValueError(
            f"{field_name} must be finite."
        )

    if allow_zero:
        valid = normalized >= 0
        requirement = "non-negative"
    else:
        valid = normalized > 0
        requirement = "positive"

    if not valid:
        raise ValueError(
            f"{field_name} must be {requirement}."
        )

    if normalized > maximum:
        raise ValueError(
            f"{field_name} must not exceed "
            f"{maximum} seconds."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class HostAgentIdentityConfig:
    """Represent host identity overrides."""

    host_id_override: str | None = None

    def __post_init__(self) -> None:
        """Validate identity settings."""
        object.__setattr__(
            self,
            "host_id_override",
            _normalize_optional_text(
                self.host_id_override,
                "host_id_override",
            ),
        )


@dataclass(frozen=True, slots=True)
class HostAgentServerConfig:
    """Represent central API connection settings."""

    base_url: str
    heartbeat_path: str
    request_timeout_seconds: float
    run_ingestion_path: str = "/api/v1/runs/ingest"

    def __post_init__(self) -> None:
        """Validate server settings."""
        base_url = _normalize_required_text(
            self.base_url,
            "base_url",
        )
        parsed_url = urlparse(base_url)

        if parsed_url.scheme not in {
            "http",
            "https",
        }:
            raise ValueError(
                "base_url must use http or https."
            )

        if not parsed_url.netloc:
            raise ValueError(
                "base_url must include a host."
            )

        heartbeat_path = _normalize_required_text(
            self.heartbeat_path,
            "heartbeat_path",
        )

        if not heartbeat_path.startswith("/"):
            raise ValueError(
                "heartbeat_path must start with '/'."
            )

        run_ingestion_path = (
            _normalize_required_text(
                self.run_ingestion_path,
                "run_ingestion_path",
            )
        )

        if not run_ingestion_path.startswith("/"):
            raise ValueError(
                "run_ingestion_path must start "
                "with '/'."
            )

        object.__setattr__(
            self,
            "base_url",
            base_url.rstrip("/"),
        )
        object.__setattr__(
            self,
            "heartbeat_path",
            heartbeat_path,
        )
        object.__setattr__(
            self,
            "run_ingestion_path",
            run_ingestion_path,
        )
        object.__setattr__(
            self,
            "request_timeout_seconds",
            _normalize_number(
                self.request_timeout_seconds,
                "request_timeout_seconds",
                maximum=_MAX_TIMEOUT_SECONDS,
            ),
        )

    @property
    def heartbeat_url(self) -> str:
        """Return the complete heartbeat URL."""
        return (
            f"{self.base_url}/"
            f"{self.heartbeat_path.lstrip('/')}"
        )


    @property
    def run_ingestion_url(self) -> str:
        """Return the complete run-ingestion URL."""
        return (
            f"{self.base_url}/"
            f"{self.run_ingestion_path.lstrip('/')}"
        )


@dataclass(frozen=True, slots=True)
class HostAgentScheduleConfig:
    """Represent heartbeat scheduling settings."""

    interval_seconds: float
    monitoring_interval_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Validate scheduling settings."""
        object.__setattr__(
            self,
            "interval_seconds",
            _normalize_number(
                self.interval_seconds,
                "interval_seconds",
                maximum=_MAX_INTERVAL_SECONDS,
            ),
        )
        object.__setattr__(
            self,
            "monitoring_interval_seconds",
            _normalize_number(
                self.monitoring_interval_seconds,
                "monitoring_interval_seconds",
                maximum=_MAX_INTERVAL_SECONDS,
            ),
        )


@dataclass(frozen=True, slots=True)
class HostAgentRetryConfig:
    """Represent bounded heartbeat retry settings."""

    max_attempts: int
    initial_backoff_seconds: float
    max_backoff_seconds: float

    def __post_init__(self) -> None:
        """Validate retry settings."""
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(
                self.max_attempts,
                int,
            )
        ):
            raise TypeError(
                "max_attempts must be an integer."
            )

        if not (
            1
            <= self.max_attempts
            <= _MAX_RETRY_ATTEMPTS
        ):
            raise ValueError(
                "max_attempts must be between 1 "
                f"and {_MAX_RETRY_ATTEMPTS}."
            )

        initial_backoff = _normalize_number(
            self.initial_backoff_seconds,
            "initial_backoff_seconds",
            maximum=_MAX_BACKOFF_SECONDS,
            allow_zero=True,
        )
        maximum_backoff = _normalize_number(
            self.max_backoff_seconds,
            "max_backoff_seconds",
            maximum=_MAX_BACKOFF_SECONDS,
            allow_zero=True,
        )

        if maximum_backoff < initial_backoff:
            raise ValueError(
                "max_backoff_seconds must be "
                "greater than or equal to "
                "initial_backoff_seconds."
            )

        object.__setattr__(
            self,
            "initial_backoff_seconds",
            initial_backoff,
        )
        object.__setattr__(
            self,
            "max_backoff_seconds",
            maximum_backoff,
        )


@dataclass(frozen=True, slots=True)
class HostAgentConfig:
    """Group all remote host-agent settings."""

    identity: HostAgentIdentityConfig
    server: HostAgentServerConfig
    schedule: HostAgentScheduleConfig
    retry: HostAgentRetryConfig

    def __post_init__(self) -> None:
        """Validate complete configuration composition."""
        expected_fields = (
            (
                "identity",
                self.identity,
                HostAgentIdentityConfig,
            ),
            (
                "server",
                self.server,
                HostAgentServerConfig,
            ),
            (
                "schedule",
                self.schedule,
                HostAgentScheduleConfig,
            ),
            (
                "retry",
                self.retry,
                HostAgentRetryConfig,
            ),
        )

        for (
            field_name,
            value,
            expected_type,
        ) in expected_fields:
            if not isinstance(
                value,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be a "
                    f"{expected_type.__name__} instance."
                )
