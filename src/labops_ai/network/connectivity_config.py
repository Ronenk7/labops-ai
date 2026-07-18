"""Validated configuration models for network connectivity monitoring."""
from dataclasses import dataclass
from ipaddress import ip_address
from math import isfinite


MAX_DNS_HOSTNAME_LENGTH = 253
MIN_TCP_PORT = 1
MAX_TCP_PORT = 65535


def _normalize_positive_number(field_name: str, value: object) -> float:
    """Validate and normalize a positive finite numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a numeric value.")

    normalized_value = float(value)

    if not isfinite(normalized_value):
        raise ValueError(f"{field_name} must be a finite value.")

    if normalized_value <= 0.0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return normalized_value


@dataclass(frozen=True, slots=True)
class DnsTestConfig:
    """Represent the hostname used for DNS resolution tests."""

    hostname: str

    def __post_init__(self) -> None:
        """Validate and normalize the DNS hostname."""
        if not isinstance(self.hostname, str):
            raise TypeError("DNS hostname must be a string.")

        normalized_hostname = self.hostname.strip()

        if not normalized_hostname:
            raise ValueError("DNS hostname must not be empty.")

        if any(character.isspace() for character in normalized_hostname):
            raise ValueError("DNS hostname must not contain whitespace.")

        if len(normalized_hostname) > MAX_DNS_HOSTNAME_LENGTH:
            raise ValueError(f"DNS hostname must not exceed {MAX_DNS_HOSTNAME_LENGTH} characters.")

        object.__setattr__(self, "hostname", normalized_hostname)


@dataclass(frozen=True, slots=True)
class TcpTestConfig:
    """Represent the direct IP target used for TCP connectivity tests."""

    host: str
    port: int

    def __post_init__(self) -> None:
        """Validate and normalize the TCP target."""
        if not isinstance(self.host, str):
            raise TypeError("TCP host must be a string.")

        try:
            validated_address = ip_address(self.host.strip())
        except ValueError as error:
            raise ValueError("TCP host must be a valid IPv4 or IPv6 address.") from error

        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("TCP port must be an integer.")

        if not MIN_TCP_PORT <= self.port <= MAX_TCP_PORT:
            raise ValueError(f"TCP port must be between {MIN_TCP_PORT} and {MAX_TCP_PORT}.")

        object.__setattr__(self, "host", str(validated_address))


@dataclass(frozen=True, slots=True)
class ConnectionSettings:
    """Represent general network connection behavior."""

    timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate and normalize the connection timeout."""
        normalized_timeout = _normalize_positive_number("Connection timeout", self.timeout_seconds)
        object.__setattr__(self, "timeout_seconds", normalized_timeout)


@dataclass(frozen=True, slots=True)
class LatencyThresholds:
    """Represent warning and critical network latency thresholds."""

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """Validate and normalize latency threshold values."""
        normalized_warning = _normalize_positive_number("Warning latency threshold", self.warning)
        normalized_critical = _normalize_positive_number("Critical latency threshold", self.critical)

        if normalized_warning >= normalized_critical:
            raise ValueError(
                "Warning latency threshold must be lower than "
                "critical latency threshold."
            )

        object.__setattr__(self, "warning", normalized_warning)
        object.__setattr__(self, "critical", normalized_critical)


@dataclass(frozen=True, slots=True)
class ConnectivityConfig:
    """Group all configuration required for connectivity monitoring."""

    dns_test: DnsTestConfig
    tcp_test: TcpTestConfig
    connection: ConnectionSettings
    latency_thresholds_ms: LatencyThresholds

    def __post_init__(self) -> None:
        """Verify that every field contains its expected model type."""
        expected_types = {
            "dns_test": DnsTestConfig,
            "tcp_test": TcpTestConfig,
            "connection": ConnectionSettings,
            "latency_thresholds_ms": LatencyThresholds,
        }

        for field_name, expected_type in expected_types.items():
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be an instance of {expected_type.__name__}.")