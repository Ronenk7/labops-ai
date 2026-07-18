"""Configuration models for network connectivity monitoring."""

from dataclasses import dataclass
from ipaddress import ip_address


def _normalize_positive_number(
    field_name: str,
    value: object,
) -> float:
    """
    Validate and normalize a positive numeric configuration value.

    Args:
        field_name:
            Human-readable name of the configuration field.

        value:
            Raw value supplied to the configuration model.

    Returns:
        The validated value converted to float.

    Raises:
        TypeError:
            If the supplied value is not an integer or float.

        ValueError:
            If the supplied value is not greater than zero.
    """
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            f"{field_name} must be a numeric value."
        )

    normalized_value = float(value)

    if normalized_value <= 0.0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return normalized_value


@dataclass(frozen=True, slots=True)
class DnsTestConfig:
    """
    Represent the target used for DNS resolution tests.

    Attributes:
        hostname:
            Domain name that the connectivity monitor attempts to
            resolve into an IP address.
    """

    hostname: str

    def __post_init__(self) -> None:
        """
        Validate and normalize the DNS hostname.

        Surrounding whitespace is removed, but whitespace inside the
        hostname is rejected.

        Raises:
            TypeError:
                If hostname is not a string.

            ValueError:
                If hostname is empty, contains whitespace, or exceeds
                the maximum supported hostname length.
        """
        if not isinstance(self.hostname, str):
            raise TypeError(
                "DNS hostname must be a string."
            )

        normalized_hostname = self.hostname.strip()

        if not normalized_hostname:
            raise ValueError(
                "DNS hostname must not be empty."
            )

        if any(
            character.isspace()
            for character in normalized_hostname
        ):
            raise ValueError(
                "DNS hostname must not contain whitespace."
            )

        if len(normalized_hostname) > 253:
            raise ValueError(
                "DNS hostname must not exceed 253 characters."
            )

        object.__setattr__(
            self,
            "hostname",
            normalized_hostname,
        )


@dataclass(frozen=True, slots=True)
class TcpTestConfig:
    """
    Represent the direct IP target used for TCP connectivity tests.

    A direct IP address is used so that TCP connectivity can be tested
    independently from DNS resolution.

    Attributes:
        host:
            IPv4 or IPv6 address used as the TCP target.

        port:
            TCP port opened during the connectivity test.
    """

    host: str
    port: int

    def __post_init__(self) -> None:
        """
        Validate and normalize the TCP target.

        Surrounding whitespace is removed from the host before the IP
        address is validated.

        Raises:
            TypeError:
                If host is not a string or port is not an integer.

            ValueError:
                If host is not a valid IPv4 or IPv6 address, or if the
                port is outside the valid TCP port range.
        """
        if not isinstance(self.host, str):
            raise TypeError(
                "TCP host must be a string."
            )

        normalized_host = self.host.strip()

        try:
            validated_address = ip_address(
                normalized_host
            )
        except ValueError as error:
            raise ValueError(
                "TCP host must be a valid IPv4 "
                "or IPv6 address."
            ) from error

        if isinstance(self.port, bool) or not isinstance(
            self.port,
            int,
        ):
            raise TypeError(
                "TCP port must be an integer."
            )

        if not 1 <= self.port <= 65535:
            raise ValueError(
                "TCP port must be between 1 and 65535."
            )

        object.__setattr__(
            self,
            "host",
            str(validated_address),
        )


@dataclass(frozen=True, slots=True)
class ConnectionSettings:
    """
    Represent general network connection behavior.

    Attributes:
        timeout_seconds:
            Maximum number of seconds allowed for a network operation
            before it is treated as failed.
    """

    timeout_seconds: float

    def __post_init__(self) -> None:
        """
        Validate and normalize the connection timeout.

        Raises:
            TypeError:
                If timeout_seconds is not numeric.

            ValueError:
                If timeout_seconds is not greater than zero.
        """
        normalized_timeout = _normalize_positive_number(
            "Connection timeout",
            self.timeout_seconds,
        )

        object.__setattr__(
            self,
            "timeout_seconds",
            normalized_timeout,
        )


@dataclass(frozen=True, slots=True)
class LatencyThresholds:
    """
    Represent warning and critical network latency thresholds.

    Attributes:
        warning:
            Latency in milliseconds at which the connection enters the
            WARNING state.

        critical:
            Latency in milliseconds at which the connection enters the
            CRITICAL state.
    """

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """
        Validate and normalize latency threshold values.

        Raises:
            TypeError:
                If either threshold is not numeric.

            ValueError:
                If either threshold is not positive, or if the warning
                threshold is not lower than the critical threshold.
        """
        normalized_warning = _normalize_positive_number(
            "Warning latency threshold",
            self.warning,
        )

        normalized_critical = _normalize_positive_number(
            "Critical latency threshold",
            self.critical,
        )

        if normalized_warning >= normalized_critical:
            raise ValueError(
                "Warning latency threshold must be lower "
                "than critical latency threshold."
            )

        object.__setattr__(
            self,
            "warning",
            normalized_warning,
        )

        object.__setattr__(
            self,
            "critical",
            normalized_critical,
        )


@dataclass(frozen=True, slots=True)
class ConnectivityConfig:
    """
    Group all configuration required for connectivity monitoring.

    Attributes:
        dns_test:
            Configuration for the DNS resolution test.

        tcp_test:
            Configuration for the direct TCP connectivity test.

        connection:
            General timeout settings for network operations.

        latency_thresholds_ms:
            Warning and critical latency thresholds in milliseconds.
    """

    dns_test: DnsTestConfig
    tcp_test: TcpTestConfig
    connection: ConnectionSettings
    latency_thresholds_ms: LatencyThresholds

    def __post_init__(self) -> None:
        """
        Verify that every field contains its expected model type.

        Raises:
            TypeError:
                If one of the fields does not contain the required
                configuration model.
        """
        expected_types = {
            "dns_test": DnsTestConfig,
            "tcp_test": TcpTestConfig,
            "connection": ConnectionSettings,
            "latency_thresholds_ms": LatencyThresholds,
        }

        for field_name, expected_type in expected_types.items():
            actual_value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                actual_value,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be an instance of "
                    f"{expected_type.__name__}."
                )