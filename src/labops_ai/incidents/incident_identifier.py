"""Generate validated sequential incident identifiers."""
from __future__ import annotations

from dataclasses import dataclass

from labops_ai.incidents.incident_config import (
    IncidentIdentifierConfig,
)


@dataclass(frozen=True, slots=True)
class IncidentIdGenerator:
    """Generate incident identifiers using external configuration."""

    config: IncidentIdentifierConfig

    def __post_init__(self) -> None:
        """Validate the identifier configuration dependency."""
        if not isinstance(self.config, IncidentIdentifierConfig):
            raise TypeError(
                "config must be an IncidentIdentifierConfig instance."
            )

    def generate(self, sequence: int) -> str:
        """Generate one incident identifier from a sequence number."""
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise TypeError(
                "Incident sequence must be an integer."
            )

        if sequence <= 0:
            raise ValueError(
                "Incident sequence must be greater than zero."
            )

        maximum_sequence = (
            10 ** self.config.sequence_width
        ) - 1

        if sequence > maximum_sequence:
            raise OverflowError(
                "Incident sequence exceeds the configured "
                "identifier width."
            )

        formatted_sequence = str(sequence).zfill(
            self.config.sequence_width
        )

        return (
            f"{self.config.prefix}"
            f"{self.config.separator}"
            f"{formatted_sequence}"
        )