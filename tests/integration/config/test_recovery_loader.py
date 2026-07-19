"""Integration tests for recovery configuration loading."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.recovery import (
    RecoveryConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.integration
CASES = load_test_fixture(
    "config/recovery_loader_cases.json"
)


def write_configuration(
    tmp_path: Path,
    configuration: object,
) -> Path:
    """Write one temporary recovery JSON file."""
    path = tmp_path / "recovery_actions.json"
    path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return path


class TestRecoveryConfigLoader:
    """Test recovery JSON configuration loading."""

    def test_loads_default_configuration(self) -> None:
        config = RecoveryConfigLoader().load()

        assert config.execution.enabled is False
        assert config.execution.dry_run is True
        assert len(config.service_rules) == 2

    def test_loads_custom_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_configuration(
            tmp_path,
            CASES["valid_configuration"],
        )

        config = RecoveryConfigLoader(path).load()

        assert config.execution.enabled is True
        assert config.service_rules[
            0
        ].trigger_statuses == (
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        )

    def test_rejects_missing_section(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration["service_rules"]

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            RecoveryConfigLoader(
                write_configuration(
                    tmp_path,
                    configuration,
                )
            ).load()

    def test_rejects_invalid_section_type(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["service_rules"] = {}

        with pytest.raises(
            ValueError,
            match="JSON array",
        ):
            RecoveryConfigLoader(
                write_configuration(
                    tmp_path,
                    configuration,
                )
            ).load()

    def test_rejects_missing_nested_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        del configuration[
            "execution"
        ]["dry_run"]

        with pytest.raises(
            ValueError,
            match="Missing required keys",
        ):
            RecoveryConfigLoader(
                write_configuration(
                    tmp_path,
                    configuration,
                )
            ).load()

    def test_rejects_unexpected_key(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["unexpected"] = True

        with pytest.raises(
            ValueError,
            match="Unsupported keys",
        ):
            RecoveryConfigLoader(
                write_configuration(
                    tmp_path,
                    configuration,
                )
            ).load()

    def test_rejects_invalid_status(
        self,
        tmp_path: Path,
    ) -> None:
        configuration = copy.deepcopy(
            CASES["valid_configuration"]
        )
        configuration["service_rules"][0][
            "trigger_statuses"
        ] = ["UNKNOWN"]

        with pytest.raises(
            ValueError,
            match="Unsupported recovery",
        ):
            RecoveryConfigLoader(
                write_configuration(
                    tmp_path,
                    configuration,
                )
            ).load()

    def test_rejects_invalid_json(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "invalid.json"
        path.write_text(
            CASES["invalid_json_text"],
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="invalid JSON",
        ):
            RecoveryConfigLoader(path).load()

    def test_rejects_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path / CASES["missing_file_name"]
        )

        with pytest.raises(
            FileNotFoundError,
            match="was not found",
        ):
            RecoveryConfigLoader(path).load()
