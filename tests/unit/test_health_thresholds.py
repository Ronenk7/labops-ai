"""Unit tests for the HealthThresholds configuration model."""

from dataclasses import FrozenInstanceError

import pytest

from labops_ai.config.health_thresholds import (
    HealthThresholds,
)


@pytest.mark.unit
class TestHealthThresholds:
    """Verify validation and immutability of threshold objects."""

    @pytest.mark.parametrize(
        ("warning", "critical"),
        [
            pytest.param(
                0.0,
                1.0,
                id="minimum-valid-range",
            ),
            pytest.param(
                25.5,
                75.5,
                id="valid-decimal-values",
            ),
            pytest.param(
                99.0,
                100.0,
                id="maximum-valid-range",
            ),
        ],
    )
    def test_accepts_valid_thresholds(
        self,
        warning: float,
        critical: float,
    ) -> None:
        """
        Verify that valid percentage ranges create an object.

        A valid configuration contains numeric percentage values
        between zero and one hundred, where warning is lower than
        critical.
        """
        thresholds = HealthThresholds(
            warning=warning,
            critical=critical,
        )

        assert thresholds.warning == float(warning)
        assert thresholds.critical == float(critical)

    @pytest.mark.parametrize(
        ("warning", "critical"),
        [
            pytest.param(
                -1.0,
                90.0,
                id="warning-below-zero",
            ),
            pytest.param(
                70.0,
                101.0,
                id="critical-above-one-hundred",
            ),
            pytest.param(
                70.0,
                -1.0,
                id="critical-below-zero",
            ),
            pytest.param(
                101.0,
                102.0,
                id="warning-above-one-hundred",
            ),
        ],
    )
    def test_rejects_values_outside_percentage_range(
        self,
        warning: float,
        critical: float,
    ) -> None:
        """
        Verify that percentages outside zero to one hundred fail.

        Invalid values must be rejected immediately so that the
        monitoring logic never receives an unusable configuration.
        """
        with pytest.raises(ValueError):
            HealthThresholds(
                warning=warning,
                critical=critical,
            )

    @pytest.mark.parametrize(
        ("warning", "critical"),
        [
            pytest.param(
                70.0,
                70.0,
                id="equal-thresholds",
            ),
            pytest.param(
                90.0,
                70.0,
                id="warning-above-critical",
            ),
        ],
    )
    def test_rejects_invalid_threshold_order(
        self,
        warning: float,
        critical: float,
    ) -> None:
        """
        Verify that warning must remain lower than critical.

        Equal or reversed thresholds would make status evaluation
        logically ambiguous.
        """
        with pytest.raises(
            ValueError,
            match="Warning threshold must be lower",
        ):
            HealthThresholds(
                warning=warning,
                critical=critical,
            )

    @pytest.mark.parametrize(
        ("warning", "critical"),
        [
            pytest.param(
                "70",
                90.0,
                id="warning-is-string",
            ),
            pytest.param(
                70.0,
                "90",
                id="critical-is-string",
            ),
            pytest.param(
                True,
                90.0,
                id="warning-is-boolean",
            ),
            pytest.param(
                70.0,
                False,
                id="critical-is-boolean",
            ),
        ],
    )
    def test_rejects_non_numeric_thresholds(
        self,
        warning: object,
        critical: object,
    ) -> None:
        """
        Verify that threshold fields accept only numeric values.

        Strings and Boolean values must not be silently converted
        into percentages.
        """
        with pytest.raises(TypeError):
            HealthThresholds(
                warning=warning,  # type: ignore[arg-type]
                critical=critical,  # type: ignore[arg-type]
            )

    def test_thresholds_are_immutable(self) -> None:
        """
        Verify that configuration cannot change after creation.

        Runtime threshold changes must happen through a new validated
        configuration object rather than accidental field mutation.
        """
        thresholds = HealthThresholds(
            warning=70.0,
            critical=90.0,
        )

        with pytest.raises(FrozenInstanceError):
            thresholds.warning = 75.0  # type: ignore[misc]