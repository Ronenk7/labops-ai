"""Integration tests for shared external JSON configuration loading."""
import json
from pathlib import Path

import pytest

from labops_ai.config.utils import load_json_config
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("config_utils_cases.json")


@pytest.mark.integration
class TestLoadJsonConfig:
    """Verify reading and parsing external JSON files."""

    def test_loads_valid_json_object(self, tmp_path: Path) -> None:
        """Verify that a valid JSON object is returned as a dictionary."""
        config_path = tmp_path / "valid.json"
        config_path.write_text(
            json.dumps(CASES["valid_object"]),
            encoding="utf-8",
        )

        assert load_json_config(config_path) == CASES["valid_object"]

    def test_rejects_invalid_json(self, tmp_path: Path) -> None:
        """Verify that malformed JSON produces a clear error."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text(
            CASES["invalid_json_text"],
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="invalid JSON"):
            load_json_config(config_path)

    def test_rejects_non_object_json_root(self, tmp_path: Path) -> None:
        """Verify that the JSON root must be an object."""
        config_path = tmp_path / "non_object.json"
        config_path.write_text(
            CASES["non_object_json_text"],
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="JSON object"):
            load_json_config(config_path)

    def test_rejects_missing_file(self, tmp_path: Path) -> None:
        """Verify that a missing configuration file is reported."""
        missing_path = tmp_path / CASES["missing_file_name"]

        with pytest.raises(FileNotFoundError, match="was not found"):
            load_json_config(missing_path)

    def test_rejects_directory_path(self, tmp_path: Path) -> None:
        """Verify that a directory cannot be loaded as JSON."""
        with pytest.raises(
            IsADirectoryError,
            match="points to a directory",
        ):
            load_json_config(tmp_path)