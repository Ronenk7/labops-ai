"""Integration tests for run history configuration."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.history import (
    RunHistoryConfig,
    RunHistoryConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/run_history_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "run_history.json",
) -> Path:
    """Write one temporary run history configuration."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestRunHistoryConfigLoader:
    """Test run history JSON configuration loading."""

    def test_loads_default_project_configuration(
        self,
    ) -> None:
        config = RunHistoryConfigLoader().load()

        assert isinstance(config, RunHistoryConfig)
        assert config.storage.database_path == (
            "runtime/run_history.sqlite3"
        )
        assert config.retention.max_runs == 1000

    def test_loads_custom_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = CASES["valid_configuration"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        config = RunHistoryConfigLoader(
            config_path
        ).load()

        assert config.storage.database_path == (
            configuration["storage"]["database_path"]
        )
        assert config.retention.max_age_days == 30
        assert config.retention.prune_on_write is False

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["retention"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            RunHistoryConfigLoader(
                config_path
            ).load()

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
            RunHistoryConfigLoader(
                config_path
            ).load()

    def test_rejects_missing_nested_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["storage"][
            "busy_timeout_seconds"
        ]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            RunHistoryConfigLoader(
                config_path
            ).load()

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
            RunHistoryConfigLoader(
                config_path
            ).load()

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
            RunHistoryConfigLoader(
                config_path
            ).load()

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
            RunHistoryConfigLoader(
                missing_path
            ).load()
