"""Integration tests for incident signal configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.incidents import (
    IncidentSignalConfigLoader,
    IncidentSignalFactoryConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/incident_signal_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "incident_signals.json",
) -> Path:
    """Write one temporary JSON configuration file."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestIncidentSignalConfigLoader:
    """Test incident signal JSON loading."""

    def test_loads_default_project_configuration(self) -> None:
        config = IncidentSignalConfigLoader().load()

        assert isinstance(
            config,
            IncidentSignalFactoryConfig,
        )
        assert config.decimal_places == 2

    def test_loads_custom_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        config_path = write_configuration(
            tmp_path,
            CASES["valid_configuration"],
        )

        config = IncidentSignalConfigLoader(
            config_path
        ).load()

        assert config.network_label_template == (
            "{check_type} {target}"
        )

    def test_rejects_missing_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["decimal_places"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            IncidentSignalConfigLoader(config_path).load()

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
            IncidentSignalConfigLoader(config_path).load()

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
            IncidentSignalConfigLoader(config_path).load()

    def test_rejects_missing_file(
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
            IncidentSignalConfigLoader(missing_path).load()