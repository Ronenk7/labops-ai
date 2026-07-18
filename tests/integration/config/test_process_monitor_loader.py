"""Integration tests for process monitor configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.processes import (
    ProcessMonitorConfig,
    ProcessMonitorConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/process_monitor_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "process_monitor.json",
) -> Path:
    """Write one temporary JSON configuration file."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestProcessMonitorConfigLoader:
    """Test cooperation between JSON and process models."""

    def test_loads_default_project_configuration(self) -> None:
        config = ProcessMonitorConfigLoader().load()

        assert isinstance(config, ProcessMonitorConfig)
        assert config.processes
        assert (
            config.collection.cpu_sample_interval_seconds
            > 0.0
        )
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

        config = ProcessMonitorConfigLoader(
            config_path
        ).load()

        assert len(config.processes) == 1
        assert (
            config.processes[0].process_name
            == configuration["processes"][0]["process_name"]
        )
        assert config.processes[0].required is True

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["processes"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            ProcessMonitorConfigLoader(config_path).load()

    def test_rejects_invalid_processes_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["processes"] = {}
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON array",
        ):
            ProcessMonitorConfigLoader(config_path).load()

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
            ProcessMonitorConfigLoader(config_path).load()

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
            ProcessMonitorConfigLoader(config_path).load()

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
            ProcessMonitorConfigLoader(missing_path).load()