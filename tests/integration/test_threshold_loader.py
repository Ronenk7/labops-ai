"""Integration tests for JSON threshold configuration loading."""

import json
from pathlib import Path

import pytest

from labops_ai.config.health_thresholds import (
    HealthThresholds,
)
from labops_ai.config.threshold_loader import (
    HealthThresholdLoader,
)


@pytest.mark.integration
class TestHealthThresholdLoader:
    """Verify cooperation between JSON files and configuration models."""

    def test_loads_default_project_configuration(
        self,
    ) -> None:
        """
        Verify that the project's real configuration file is valid.

        This test connects the default JSON file, loader, and
        HealthThresholds validation model.
        """
        thresholds = HealthThresholdLoader().load()

        assert isinstance(
            thresholds,
            HealthThresholds,
        )

        assert (
            thresholds.warning
            < thresholds.critical
        )

    def test_loads_thresholds_from_custom_json_file(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify that a custom JSON file becomes a threshold object.

        The temporary file prevents the test from modifying the real
        project configuration.
        """
        config_path = (
            tmp_path
            / "health_thresholds.json"
        )

        config_path.write_text(
            json.dumps(
                {
                    "warning": 65.0,
                    "critical": 85.0,
                }
            ),
            encoding="utf-8",
        )

        loader = HealthThresholdLoader(
            config_path=config_path,
        )

        thresholds = loader.load()

        assert thresholds == HealthThresholds(
            warning=65.0,
            critical=85.0,
        )

    def test_rejects_missing_required_key(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify that incomplete JSON configuration is rejected.

        Both warning and critical fields are required to construct a
        valid HealthThresholds object.
        """
        config_path = (
            tmp_path
            / "missing_key.json"
        )

        config_path.write_text(
            json.dumps(
                {
                    "warning": 70.0,
                }
            ),
            encoding="utf-8",
        )

        loader = HealthThresholdLoader(
            config_path=config_path,
        )

        with pytest.raises(
            ValueError,
            match="Missing required threshold keys",
        ):
            loader.load()

    def test_rejects_invalid_json(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify that malformed JSON produces a clear error.

        The loader must not continue when the configuration file
        cannot be parsed safely.
        """
        config_path = (
            tmp_path
            / "invalid.json"
        )

        config_path.write_text(
            '{"warning": 70.0,',
            encoding="utf-8",
        )

        loader = HealthThresholdLoader(
            config_path=config_path,
        )

        with pytest.raises(
            ValueError,
            match="invalid JSON",
        ):
            loader.load()

    def test_rejects_missing_configuration_file(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify that a missing file produces a clear exception.

        The error must include enough information to locate the
        missing configuration.
        """
        missing_path = (
            tmp_path
            / "does_not_exist.json"
        )

        loader = HealthThresholdLoader(
            config_path=missing_path,
        )

        with pytest.raises(
            FileNotFoundError,
            match="was not found",
        ):
            loader.load()