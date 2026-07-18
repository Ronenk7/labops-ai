"""Unit tests for network connectivity configuration models."""
from typing import Any

import pytest

from labops_ai.network.connectivity_config import (
    ConnectionSettings,
    ConnectivityConfig,
    DnsTestConfig,
    LatencyThresholds,
    NetworkReportConfig,
    TcpTestConfig,
)
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("network/connectivity_config_cases.json")
REPORT_CASES = load_test_fixture(
    "network/connectivity_report_config_cases.json"
)
VALID_REPORT = REPORT_CASES["valid_report"]


@pytest.mark.unit
class TestConnectivityConfig:
    """Verify creation of complete connectivity configurations."""

    def test_creates_valid_connectivity_configuration(self) -> None:
        """Verify that complete external settings create all models."""
        case = CASES["valid_configuration"]

        config = ConnectivityConfig(
            dns_test=DnsTestConfig(**case["dns_test"]),
            tcp_test=TcpTestConfig(**case["tcp_test"]),
            connection=ConnectionSettings(**case["connection"]),
            latency_thresholds_ms=LatencyThresholds(
                **case["latency_thresholds_ms"]
            ),
            report=NetworkReportConfig(**VALID_REPORT),
        )

        assert config.dns_test.hostname == case["dns_test"]["hostname"]
        assert config.tcp_test.host == case["tcp_test"]["host"]
        assert config.tcp_test.port == case["tcp_test"]["port"]
        assert config.connection.timeout_seconds == float(
            case["connection"]["timeout_seconds"]
        )
        assert config.report.title == VALID_REPORT["title"]


@pytest.mark.unit
class TestDnsTestConfig:
    """Verify DNS target validation and normalization."""

    def test_strips_surrounding_whitespace_from_hostname(self) -> None:
        """Verify that harmless surrounding whitespace is removed."""
        case = CASES["dns_normalization"]
        config = DnsTestConfig(hostname=case["input"])

        assert config.hostname == case["expected"]

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_hostnames"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_hostname_values(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that unusable hostname values are rejected."""
        with pytest.raises(ValueError):
            DnsTestConfig(hostname=case["value"])

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_hostname_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_string_hostname(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that the DNS hostname accepts only strings."""
        with pytest.raises(TypeError):
            DnsTestConfig(hostname=case["value"])


@pytest.mark.unit
class TestTcpTestConfig:
    """Verify TCP target validation and normalization."""

    @pytest.mark.parametrize(
        "case",
        CASES["valid_ip_addresses"],
        ids=lambda case: case["id"],
    )
    def test_accepts_and_normalizes_valid_ip_addresses(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that valid IPv4 and IPv6 addresses are accepted."""
        config = TcpTestConfig(
            host=case["input"],
            port=CASES["valid_port"],
        )

        assert config.host == case["expected"]

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_ip_addresses"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_ip_addresses(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that the TCP target must contain a valid IP address."""
        with pytest.raises(
            ValueError,
            match="TCP host must be a valid",
        ):
            TcpTestConfig(
                host=case["value"],
                port=CASES["valid_port"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_host_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_string_host(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that the TCP host accepts only strings."""
        with pytest.raises(TypeError):
            TcpTestConfig(
                host=case["value"],
                port=CASES["valid_port"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_ports"],
        ids=lambda case: case["id"],
    )
    def test_rejects_port_outside_valid_range(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that the TCP port remains inside the legal range."""
        host = CASES["valid_configuration"]["tcp_test"]["host"]

        with pytest.raises(
            ValueError,
            match="TCP port must be between",
        ):
            TcpTestConfig(
                host=host,
                port=case["value"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_port_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_integer_port(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that the TCP port accepts only integers."""
        host = CASES["valid_configuration"]["tcp_test"]["host"]

        with pytest.raises(TypeError):
            TcpTestConfig(
                host=host,
                port=case["value"],
            )


@pytest.mark.unit
class TestConnectionSettings:
    """Verify network timeout validation."""

    def test_accepts_and_normalizes_valid_timeout(self) -> None:
        """Verify that valid timeout values are normalized to float."""
        case = CASES["valid_connection_timeout"]
        config = ConnectionSettings(timeout_seconds=case["input"])

        assert config.timeout_seconds == case["expected"]

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_connection_timeouts"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_timeouts(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that invalid timeout values fail validation."""
        expected_error = (
            TypeError
            if isinstance(case["value"], (str, bool))
            or case["value"] is None
            else ValueError
        )

        with pytest.raises(expected_error):
            ConnectionSettings(timeout_seconds=case["value"])


@pytest.mark.unit
class TestLatencyThresholds:
    """Verify latency threshold validation."""

    def test_accepts_valid_latency_thresholds(self) -> None:
        """Verify that valid latency thresholds are normalized."""
        case = CASES["valid_latency_thresholds"]
        thresholds = LatencyThresholds(**case)

        assert thresholds.warning == float(case["warning"])
        assert thresholds.critical == float(case["critical"])

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_latency_order"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_latency_order(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that warning latency must be lower than critical."""
        with pytest.raises(ValueError, match="must be lower"):
            LatencyThresholds(
                warning=case["warning"],
                critical=case["critical"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_latency_values"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_latency_values(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that invalid latency values fail validation."""
        has_invalid_type = any(
            isinstance(case[field_name], (str, bool))
            or case[field_name] is None
            for field_name in ("warning", "critical")
        )

        expected_error = TypeError if has_invalid_type else ValueError

        with pytest.raises(expected_error):
            LatencyThresholds(
                warning=case["warning"],
                critical=case["critical"],
            )