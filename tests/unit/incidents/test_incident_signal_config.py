"""Unit tests for incident signal formatting configuration."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.incidents import IncidentSignalFactoryConfig
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "config/incident_signal_loader_cases.json"
)


class TestIncidentSignalFactoryConfig:
    """Test externally configured signal formatting."""

    def test_accepts_complete_configuration(self) -> None:
        config = IncidentSignalFactoryConfig(
            **CASES["valid_configuration"]
        )

        assert config.decimal_places == 2
        assert "{label}" in (
            config.system_description_template
        )

    @pytest.mark.parametrize(
        "decimal_places",
        [-1, 7, "2", True],
        ids=[
            "negative",
            "above-maximum",
            "string",
            "boolean",
        ],
    )
    def test_rejects_invalid_decimal_places(
        self,
        decimal_places: Any,
    ) -> None:
        values = dict(CASES["valid_configuration"])
        values["decimal_places"] = decimal_places

        with pytest.raises((TypeError, ValueError)):
            IncidentSignalFactoryConfig(**values)

    def test_rejects_missing_template_field(self) -> None:
        values = dict(CASES["valid_configuration"])
        values["system_description_template"] = (
            "{label}: {value}"
        )

        with pytest.raises(
            ValueError,
            match="exactly these fields",
        ):
            IncidentSignalFactoryConfig(**values)

    def test_rejects_unexpected_template_field(self) -> None:
        values = dict(CASES["valid_configuration"])
        values["network_label_template"] = (
            "{check_type} {target} {unexpected}"
        )

        with pytest.raises(
            ValueError,
            match="exactly these fields",
        ):
            IncidentSignalFactoryConfig(**values)