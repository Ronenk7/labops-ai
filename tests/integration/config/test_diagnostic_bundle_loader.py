"""Integration tests for diagnostic bundle configuration."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.diagnostics import (
    DiagnosticBundleConfig,
    DiagnosticBundleConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/diagnostic_bundle_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
    file_name: str = "diagnostic_bundle.json",
) -> Path:
    """Write one temporary diagnostic configuration."""
    config_path = tmp_path / file_name
    config_path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return config_path


class TestDiagnosticBundleConfigLoader:
    """Test diagnostic JSON configuration loading."""

    def test_loads_default_project_configuration(self) -> None:
        config = DiagnosticBundleConfigLoader().load()

        assert isinstance(config, DiagnosticBundleConfig)
        assert config.output.archive_prefix == (
            "labops-diagnostic"
        )
        assert config.collection.include_json_report is True

    def test_loads_custom_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = CASES["valid_configuration"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        config = DiagnosticBundleConfigLoader(
            config_path
        ).load()

        assert config.output.directory == (
            configuration["output"]["directory"]
        )
        assert config.files.manifest_name == (
            configuration["files"]["manifest_name"]
        )

    def test_rejects_missing_required_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["collection"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            DiagnosticBundleConfigLoader(
                config_path
            ).load()

    def test_rejects_invalid_section_type(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["output"] = []
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="must be a JSON object",
        ):
            DiagnosticBundleConfigLoader(
                config_path
            ).load()

    def test_rejects_missing_nested_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["files"]["manifest_name"]
        config_path = write_configuration(
            tmp_path,
            configuration,
        )

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            DiagnosticBundleConfigLoader(
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
            DiagnosticBundleConfigLoader(
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
            DiagnosticBundleConfigLoader(
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
            DiagnosticBundleConfigLoader(
                missing_path
            ).load()