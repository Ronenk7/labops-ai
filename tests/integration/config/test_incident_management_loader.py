"""Integration tests for incident configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.incidents import (
    IncidentManagementConfig,
    IncidentManagementConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/incident_management_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "incident_management.json",
) -> Path:
    """Write one temporary JSON configuration file."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestIncidentManagementConfigLoader:
    """Test cooperation between JSON and incident models."""

    def test_loads_default_project_configuration(self) -> None:
        config = IncidentManagementConfigLoader().load()

        assert isinstance(config, IncidentManagementConfig)
        assert config.storage.path
        assert config.identifier.prefix == "INC"
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

        config = IncidentManagementConfigLoader(
            config_path
        ).load()

        assert (
            config.storage.path
            == configuration["storage"]["path"]
        )
        assert (
            config.identifier.sequence_width
            == configuration["identifier"]["sequence_width"]
        )

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["identifier"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            IncidentManagementConfigLoader(config_path).load()

    def test_rejects_invalid_section_type(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["storage"] = []
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON object",
        ):
            IncidentManagementConfigLoader(config_path).load()

    def test_rejects_missing_nested_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["identifier"]["sequence_width"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            IncidentManagementConfigLoader(config_path).load()

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
            IncidentManagementConfigLoader(config_path).load()

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
            IncidentManagementConfigLoader(config_path).load()

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
            IncidentManagementConfigLoader(missing_path).load()