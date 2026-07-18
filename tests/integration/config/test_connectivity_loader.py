"""Integration tests for external connectivity configuration loading."""
import json
from pathlib import Path

import pytest

from labops_ai.network import ConnectivityConfig, ConnectivityConfigLoader
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("config/connectivity_loader_cases.json")


@pytest.mark.integration
class TestConnectivityConfigLoader:
    """Verify cooperation between JSON files and connectivity models."""

    def test_loads_default_project_configuration(self) -> None:
        """Verify that the project's real external configuration is valid."""
        config = ConnectivityConfigLoader().load()

        assert isinstance(config, ConnectivityConfig)
        assert config.dns_test.hostname
        assert config.tcp_test.host
        assert config.connection.timeout_seconds > 0.0
        assert (
            config.latency_thresholds_ms.warning
            < config.latency_thresholds_ms.critical
        )

    def test_loads_custom_configuration(self, tmp_path: Path) -> None:
        """Verify conversion of custom JSON into configuration models."""
        config_path = tmp_path / "network_connectivity.json"
        config_path.write_text(
            json.dumps(CASES["valid_custom_configuration"]),
            encoding="utf-8",
        )

        config = ConnectivityConfigLoader(config_path).load()
        expected = CASES["valid_custom_configuration"]

        assert config.dns_test.hostname == expected["dns_test"]["hostname"]
        assert config.tcp_test.host == expected["tcp_test"]["host"]
        assert config.tcp_test.port == expected["tcp_test"]["port"]
        assert config.connection.timeout_seconds == expected["connection"][
            "timeout_seconds"
        ]

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify that incomplete top-level configuration is rejected."""
        config_path = tmp_path / "missing_section.json"
        config_path.write_text(
            json.dumps(CASES["missing_section_configuration"]),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Missing required keys"):
            ConnectivityConfigLoader(config_path).load()

    def test_rejects_invalid_section_type(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify that each required section must be a JSON object."""
        config_path = tmp_path / "invalid_section.json"
        config_path.write_text(
            json.dumps(CASES["invalid_section_type_configuration"]),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON object",
        ):
            ConnectivityConfigLoader(config_path).load()

    def test_rejects_missing_nested_field(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify that missing fields inside sections are rejected."""
        config_path = tmp_path / "missing_field.json"
        config_path.write_text(
            json.dumps(CASES["missing_nested_field_configuration"]),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Missing required keys"):
            ConnectivityConfigLoader(config_path).load()

    def test_rejects_unexpected_key(self, tmp_path: Path) -> None:
        """Verify that unsupported keys cannot pass silently."""
        config_path = tmp_path / "unexpected_key.json"
        config_path.write_text(
            json.dumps(CASES["unexpected_key_configuration"]),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Unsupported keys"):
            ConnectivityConfigLoader(config_path).load()

    def test_rejects_invalid_json(self, tmp_path: Path) -> None:
        """Verify that malformed JSON produces a clear error."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text(
            CASES["invalid_json_text"],
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="invalid JSON"):
            ConnectivityConfigLoader(config_path).load()

    def test_rejects_missing_configuration_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify that a missing file produces a clear exception."""
        missing_path = tmp_path / CASES["missing_file_name"]

        with pytest.raises(FileNotFoundError, match="was not found"):
            ConnectivityConfigLoader(missing_path).load()