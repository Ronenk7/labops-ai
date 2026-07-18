"""Load system health thresholds from a JSON configuration file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from labops_ai.config.health_thresholds import HealthThresholds

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_THRESHOLDS_PATH = (
        PROJECT_ROOT
        / "config"
        / "health_thresholds.json"
)


class HealthThresholdLoader:
    """
    Load and validate health thresholds from a JSON file.

    The loader is responsible only for reading configuration data
    and converting it into a validated HealthThresholds object.
    """

    def __init__(
            self,
            config_path: str | Path = DEFAULT_THRESHOLDS_PATH,
    ) -> None:
        """
        Initialize the loader with a configuration file path.

        Args:
            config_path:
                Path to the JSON configuration file. When omitted,
                the project's default health_thresholds.json file is
                used.
        """
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        """Return the JSON configuration path used by the loader."""
        return self._config_path

    def load(self) -> HealthThresholds:
        """
        Read, parse, and validate the threshold configuration.

        Returns:
            A validated HealthThresholds object.

        Raises:
            FileNotFoundError:
                If the configuration file does not exist.

            ValueError:
                If the file contains invalid JSON, does not contain
                a JSON object, or is missing required fields.

            TypeError:
                If threshold values are not numeric.
        """
        configuration = self._read_json()

        required_keys = {
            "warning",
            "critical",
        }

        missing_keys = required_keys.difference(
            configuration.keys()
        )

        if missing_keys:
            formatted_keys = ", ".join(
                sorted(missing_keys)
            )

            raise ValueError(
                "Missing required threshold keys: "
                f"{formatted_keys}."
            )

        return HealthThresholds(
            warning=configuration["warning"],
            critical=configuration["critical"],
        )

    def _read_json(self) -> dict[str, Any]:
        """
        Read and parse the configured JSON file.

        Returns:
            The parsed JSON object as a dictionary.

        Raises:
            FileNotFoundError:
                If the configuration file cannot be found.

            ValueError:
                If the file contains invalid JSON or its root value
                is not a JSON object.
        """
        try:
            raw_content = self._config_path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError as error:
            raise FileNotFoundError(
                "Threshold configuration file was not found: "
                f"{self._config_path}"
            ) from error

        try:
            configuration = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Threshold configuration contains invalid JSON: "
                f"{self._config_path}"
            ) from error

        if not isinstance(configuration, dict):
            raise ValueError(
                "Threshold configuration must contain "
                "a JSON object."
            )

        return configuration