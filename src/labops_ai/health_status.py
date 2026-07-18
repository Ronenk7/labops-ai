"""Shared health severity levels used across LabOps AI."""
from enum import StrEnum


class HealthStatus(StrEnum):
    """Define the supported health severity levels."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"