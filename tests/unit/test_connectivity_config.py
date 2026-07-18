"""Unit tests for network connectivity configuration models."""

import pytest

from labops_ai.network.connectivity_config import (
    ConnectionSettings,
    ConnectivityConfig,
    DnsTestConfig,
    LatencyThresholds,
    TcpTestConfig,
)


@pytest.mark.unit
class TestConnectivityConfig:
    """Verify creation of complete network connectivity configurations."""

    def test_creates_valid_connectivity_configuration(
        self,
    ) -> None:
        """
        Verify that valid settings create a complete configuration.

        The test confirms that all nested configuration models are
        accepted and that numeric values are normalized correctly.
        """
        config = ConnectivityConfig(
            dns_test=DnsTestConfig(
                hostname="www.cloudflare.com",
            ),
            tcp_test=TcpTestConfig(
                host="1.1.1.1",
                port=443,
            ),
            connection=ConnectionSettings(
                timeout_seconds=3,
            ),
            latency_thresholds_ms=LatencyThresholds(
                warning=250,
                critical=1000,
            ),
        )

        assert (
            config.dns_test.hostname
            == "www.cloudflare.com"
        )
        assert config.tcp_test.host == "1.1.1.1"
        assert config.tcp_test.port == 443
        assert (
            config.connection.timeout_seconds
            == 3.0
        )
        assert (
            config.latency_thresholds_ms.warning
            == 250.0
        )
        assert (
            config.latency_thresholds_ms.critical
            == 1000.0
        )


@pytest.mark.unit
class TestDnsTestConfig:
    """Verify validation and normalization of DNS test settings."""

    def test_strips_surrounding_whitespace_from_hostname(
        self,
    ) -> None:
        """
        Verify that harmless surrounding whitespace is removed.

        Configuration values may contain accidental spaces around the
        hostname, but the stored hostname must remain normalized.
        """
        config = DnsTestConfig(
            hostname="  www.cloudflare.com  ",
        )

        assert (
            config.hostname
            == "www.cloudflare.com"
        )

    @pytest.mark.parametrize(
        "hostname",
        [
            pytest.param(
                "",
                id="empty-hostname",
            ),
            pytest.param(
                "   ",
                id="whitespace-only-hostname",
            ),
            pytest.param(
                "www.cloudflare .com",
                id="hostname-containing-whitespace",
            ),
            pytest.param(
                "a" * 254,
                id="hostname-exceeds-maximum-length",
            ),
        ],
    )
    def test_rejects_invalid_hostname_values(
        self,
        hostname: str,
    ) -> None:
        """
        Verify that unusable hostname values are rejected.

        A DNS hostname must not be empty, contain whitespace, or exceed
        the maximum supported hostname length.
        """
        with pytest.raises(ValueError):
            DnsTestConfig(
                hostname=hostname,
            )

    @pytest.mark.parametrize(
        "hostname",
        [
            pytest.param(
                123,
                id="hostname-is-integer",
            ),
            pytest.param(
                True,
                id="hostname-is-boolean",
            ),
            pytest.param(
                None,
                id="hostname-is-none",
            ),
        ],
    )
    def test_rejects_non_string_hostname(
        self,
        hostname: object,
    ) -> None:
        """
        Verify that the DNS hostname accepts only string values.

        Invalid data types must fail instead of being silently
        converted into text.
        """
        with pytest.raises(TypeError):
            DnsTestConfig(
                hostname=hostname,  # type: ignore[arg-type]
            )

@pytest.mark.unit
class TestTcpTestConfig:
    """Verify validation and normalization of TCP test settings."""

    @pytest.mark.parametrize(
        ("host", "expected_host"),
        [
            pytest.param(
                "1.1.1.1",
                "1.1.1.1",
                id="valid-ipv4-address",
            ),
            pytest.param(
                "  1.1.1.1  ",
                "1.1.1.1",
                id="ipv4-with-surrounding-whitespace",
            ),
            pytest.param(
                "2001:4860:4860::8888",
                "2001:4860:4860::8888",
                id="valid-ipv6-address",
            ),
        ],
    )
    def test_accepts_and_normalizes_valid_ip_addresses(
        self,
        host: str,
        expected_host: str,
    ) -> None:
        """
        Verify that valid IPv4 and IPv6 addresses are accepted.

        Harmless surrounding whitespace must be removed before the
        address is stored in the configuration object.
        """
        config = TcpTestConfig(
            host=host,
            port=443,
        )

        assert config.host == expected_host
        assert config.port == 443

    @pytest.mark.parametrize(
        "host",
        [
            pytest.param(
                "",
                id="empty-host",
            ),
            pytest.param(
                "cloudflare.com",
                id="hostname-instead-of-ip-address",
            ),
            pytest.param(
                "999.999.999.999",
                id="invalid-ipv4-address",
            ),
            pytest.param(
                "1.1.1",
                id="incomplete-ipv4-address",
            ),
        ],
    )
    def test_rejects_invalid_ip_addresses(
        self,
        host: str,
    ) -> None:
        """
        Verify that the TCP target must contain a valid IP address.

        A hostname is intentionally rejected because the TCP test must
        remain independent from the DNS resolution test.
        """
        with pytest.raises(
            ValueError,
            match="TCP host must be a valid",
        ):
            TcpTestConfig(
                host=host,
                port=443,
            )

    @pytest.mark.parametrize(
        "host",
        [
            pytest.param(
                123,
                id="host-is-integer",
            ),
            pytest.param(
                True,
                id="host-is-boolean",
            ),
            pytest.param(
                None,
                id="host-is-none",
            ),
        ],
    )
    def test_rejects_non_string_host(
        self,
        host: object,
    ) -> None:
        """Verify that the TCP host accepts only string values."""
        with pytest.raises(TypeError):
            TcpTestConfig(
                host=host,  # type: ignore[arg-type]
                port=443,
            )

    @pytest.mark.parametrize(
        "port",
        [
            pytest.param(
                0,
                id="port-below-valid-range",
            ),
            pytest.param(
                65536,
                id="port-above-valid-range",
            ),
            pytest.param(
                -1,
                id="negative-port",
            ),
        ],
    )
    def test_rejects_port_outside_valid_range(
        self,
        port: int,
    ) -> None:
        """Verify that a TCP port must be between 1 and 65535."""
        with pytest.raises(
            ValueError,
            match="TCP port must be between",
        ):
            TcpTestConfig(
                host="1.1.1.1",
                port=port,
            )

    @pytest.mark.parametrize(
        "port",
        [
            pytest.param(
                "443",
                id="port-is-string",
            ),
            pytest.param(
                443.0,
                id="port-is-float",
            ),
            pytest.param(
                True,
                id="port-is-boolean",
            ),
            pytest.param(
                None,
                id="port-is-none",
            ),
        ],
    )
    def test_rejects_non_integer_port(
        self,
        port: object,
    ) -> None:
        """Verify that the TCP port accepts only integer values."""
        with pytest.raises(TypeError):
            TcpTestConfig(
                host="1.1.1.1",
                port=port,  # type: ignore[arg-type]
            )