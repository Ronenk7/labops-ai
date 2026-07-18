"""Integration tests for service monitor configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.services import (
    ServiceMonitorConfig,
    ServiceMonitorConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/service_monitor_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "service_monitor.json",
) -> Path:
    """Write one temporary JSON configuration file."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestServiceMonitorConfigLoader:
    """Test cooperation between JSON and service models."""

    def test_loads_default_project_configuration(self) -> None:
        config = ServiceMonitorConfigLoader().load()

        assert isinstance(config, ServiceMonitorConfig)
        assert config.services
        assert config.command.timeout_seconds > 0.0
        assert config.report.title

    def test_loads_custom_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = CASES["valid_configuration"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        config = ServiceMonitorConfigLoader(
            config_path
        ).load()

        assert (
            config.command.executable
            == configuration["command"]["executable"]
        )
        assert len(config.services) == 2
        assert (
            config.services[0].service_name
            == configuration["services"][0]["service_name"]
        )

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["services"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            ServiceMonitorConfigLoader(config_path).load()

    def test_rejects_invalid_services_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["services"] = {}
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON array",
        ):
            ServiceMonitorConfigLoader(config_path).load()

    def test_rejects_unexpected_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["unexpected"] = "value"
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Unsupported keys",
        ):
            ServiceMonitorConfigLoader(config_path).load()

    def test_rejects_invalid_json(
        self,
        tmp_path: Path,
    ) -> None:
        config_path = tmp_path / "invalid.json"
        config_path.write_text(
            CASES["invalid_json_text"],
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="invalid JSON",
        ):
            ServiceMonitorConfigLoader(config_path).load()

    def test_rejects_missing_configuration_file(
        self,
        tmp_path: Path,
    ) -> None:
        missing_path = (
            tmp_path / CASES["missing_file_name"]
        )

        with pytest.raises(
            FileNotFoundError,
            match="was not found",
        ):
            ServiceMonitorConfigLoader(missing_path).load()