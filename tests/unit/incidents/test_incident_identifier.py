"""Unit tests for sequential incident identifiers."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.incidents import (
    IncidentIdGenerator,
    IncidentIdentifierConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_store_cases.json"
)


def build_generator() -> IncidentIdGenerator:
    """Build a valid configured incident ID generator."""
    return IncidentIdGenerator(
        config=IncidentIdentifierConfig(
            **CASES["identifier"]
        )
    )


class TestIncidentIdGenerator:
    """Test sequential incident identifier generation."""

    @pytest.mark.parametrize(
        ("sequence", "expected_identifier"),
        [
            (1, "INC-000001"),
            (42, "INC-000042"),
            (999999, "INC-999999"),
        ],
    )
    def test_generates_zero_padded_identifier(
        self,
        sequence: int,
        expected_identifier: str,
    ) -> None:
        generator = build_generator()

        assert (
            generator.generate(sequence)
            == expected_identifier
        )

    @pytest.mark.parametrize(
        "sequence",
        [0, -1],
        ids=["zero-sequence", "negative-sequence"],
    )
    def test_rejects_non_positive_sequence(
        self,
        sequence: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="greater than zero",
        ):
            build_generator().generate(sequence)

    @pytest.mark.parametrize(
        "sequence",
        ["1", 1.5, True, None],
        ids=[
            "string-sequence",
            "float-sequence",
            "boolean-sequence",
            "null-sequence",
        ],
    )
    def test_rejects_non_integer_sequence(
        self,
        sequence: Any,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="must be an integer",
        ):
            build_generator().generate(sequence)

    def test_rejects_sequence_width_overflow(self) -> None:
        with pytest.raises(
            OverflowError,
            match="exceeds",
        ):
            build_generator().generate(1000000)

    def test_rejects_invalid_configuration(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncidentIdentifierConfig",
        ):
            IncidentIdGenerator(config=object())