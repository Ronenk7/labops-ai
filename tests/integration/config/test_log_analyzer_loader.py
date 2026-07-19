"""Integration tests for log analyzer configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.logs import (
    LogAnalyzerConfig,
    LogAnalyzerConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/log_analyzer_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "log_analyzer.json",
) -> Path:
    """Write one temporary JSON configuration file."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestLogAnalyzerConfigLoader:
    """Test cooperation between JSON and log models."""

    def test_loads_default_project_configuration(self) -> None:
        config = LogAnalyzerConfigLoader().load()

        assert isinstance(config, LogAnalyzerConfig)
        assert config.sources
        assert config.rules
        assert config.collection.max_lines_per_source > 0
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

        config = LogAnalyzerConfigLoader(
            config_path
        ).load()

        assert len(config.sources) == 1
        assert len(config.rules) == 1
        assert (
            config.sources[0].source_id
            == configuration["sources"][0]["source_id"]
        )
        assert (
            config.rules[0].rule_id
            == configuration["rules"][0]["rule_id"]
        )

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["rules"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            LogAnalyzerConfigLoader(config_path).load()

    def test_rejects_invalid_sources_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["sources"] = {}
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON array",
        ):
            LogAnalyzerConfigLoader(config_path).load()

    def test_rejects_invalid_nested_rule(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["rules"][0]["pattern"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            LogAnalyzerConfigLoader(config_path).load()

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
            LogAnalyzerConfigLoader(config_path).load()

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
            LogAnalyzerConfigLoader(config_path).load()

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
            LogAnalyzerConfigLoader(missing_path).load()