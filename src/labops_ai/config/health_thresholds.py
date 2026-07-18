"""Configuration model for system health thresholds."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthThresholds:
    """
    Represent validated warning and critical utilization thresholds.

    Both thresholds are percentages between 0 and 100.
    The warning threshold must be lower than the critical threshold.

    Attributes:
        warning:
            The percentage at which a metric enters the WARNING state.

        critical:
            The percentage at which a metric enters the CRITICAL state.
    """

    warning: float
    critical: float

    def __post_init__(self) -> None:
        """
        Validate and normalize threshold values after object creation.

        Raises:
            TypeError:
                If either threshold is not a numeric value.

            ValueError:
                If a threshold is outside the valid percentage range,
                or if the warning threshold is not lower than the
                critical threshold.
        """
        self._validate_numeric_value("warning", self.warning)
        self._validate_numeric_value("critical", self.critical)

        normalized_warning = float(self.warning)
        normalized_critical = float(self.critical)

        if not 0.0 <= normalized_warning <= 100.0:
            raise ValueError(
                "Warning threshold must be between 0 and 100."
            )

        if not 0.0 <= normalized_critical <= 100.0:
            raise ValueError(
                "Critical threshold must be between 0 and 100."
            )

        if normalized_warning >= normalized_critical:
            raise ValueError(
                "Warning threshold must be lower than "
                "critical threshold."
            )

        object.__setattr__(
            self,
            "warning",
            normalized_warning,
        )
        object.__setattr__(
            self,
            "critical",
            normalized_critical,
        )

    @staticmethod
    def _validate_numeric_value(
        field_name: str,
        value: object,
    ) -> None:
        """
        Verify that a threshold contains a valid numeric type.

        Boolean values are rejected even though bool inherits from int
        in Python.

        Args:
            field_name:
                Name of the field being validated.

            value:
                Value supplied to the field.

        Raises:
            TypeError:
                If the supplied value is not an integer or float.
        """
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                f"{field_name.capitalize()} threshold "
                "must be a numeric value."
            )