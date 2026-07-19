"""Orchestrate incident processing for complete monitoring runs."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from labops_ai.health_status import HealthStatus
from labops_ai.incidents.incident_manager import IncidentManager
from labops_ai.incidents.incident_models import (
    IncidentActionResult,
    IncidentSignal,
)
from labops_ai.incidents.incident_store import IncidentStoreState
from labops_ai.logs import LogAnalysisSummary
from labops_ai.network import NetworkConnectivitySummary
from labops_ai.processes import ProcessMonitoringSummary
from labops_ai.services import ServiceMonitoringSummary


class IncidentSignalBuilder(Protocol):
    """Describe the signal factory required by the pipeline."""

    def from_all(
        self,
        *,
        system_metrics: Mapping[str, float],
        system_statuses: Mapping[str, HealthStatus],
        system_metric_labels: Mapping[str, str],
        network_summary: NetworkConnectivitySummary,
        service_summary: ServiceMonitoringSummary,
        process_summary: ProcessMonitoringSummary,
        log_summary: LogAnalysisSummary,
        observed_at: datetime,
    ) -> tuple[IncidentSignal, ...]:
        """Create incident signals from every monitoring domain."""


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class IncidentProcessingSummary:
    """Represent the outcome of one complete incident run."""

    actions: tuple[IncidentActionResult, ...]
    state: IncidentStoreState

    def __post_init__(self) -> None:
        """Validate actions and resulting persisted state."""
        if not isinstance(self.actions, tuple):
            raise TypeError(
                "actions must be a tuple of "
                "IncidentActionResult instances."
            )

        for action in self.actions:
            if not isinstance(action, IncidentActionResult):
                raise TypeError(
                    "Every action must be an "
                    "IncidentActionResult instance."
                )

        if not isinstance(self.state, IncidentStoreState):
            raise TypeError(
                "state must be an IncidentStoreState instance."
            )


@dataclass(frozen=True, slots=True)
class IncidentPipeline:
    """Convert monitoring output into persisted incident changes."""

    signal_factory: IncidentSignalBuilder
    manager: IncidentManager
    clock: Callable[[], datetime] = utc_now

    def __post_init__(self) -> None:
        """Validate pipeline dependencies."""
        if not callable(
            getattr(self.signal_factory, "from_all", None)
        ):
            raise TypeError(
                "signal_factory must provide a callable "
                "from_all method."
            )

        if not isinstance(self.manager, IncidentManager):
            raise TypeError(
                "manager must be an IncidentManager instance."
            )

        TypeError(
                "manager must be an IncidentManager instance."
            )

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def run(
        self,
        *,
        system_metrics: Mapping[str, float],
        system_statuses: Mapping[str, HealthStatus],
        system_metric_labels: Mapping[str, str],
        network_summary: NetworkConnectivitySummary,
        service_summary: ServiceMonitoringSummary,
        process_summary: ProcessMonitoringSummary,
        log_summary: LogAnalysisSummary,
    ) -> IncidentProcessingSummary:
        """Process the results of one complete monitoring run."""
        observed_at = self._get_observed_at()

        signals = self.signal_factory.from_all(
            system_metrics=system_metrics,
            system_statuses=system_statuses,
            system_metric_labels=system_metric_labels,
            network_summary=network_summary,
            service_summary=service_summary,
            process_summary=process_summary,
            log_summary=log_summary,
            observed_at=observed_at,
        )

        if not isinstance(signals, tuple):
            raise TypeError(
                "Incident signal factory must return a tuple."
            )

        for signal in signals:
            if not isinstance(signal, IncidentSignal):
                raise TypeError(
                    "Incident signal factory must return only "
                    "IncidentSignal instances."
                )

        actions = self.manager.process_signals(signals)
        state = self.manager.store.load()

        if not isinstance(state, IncidentStoreState):
            raise TypeError(
                "Incident store must return an "
                "IncidentStoreState instance."
            )

        return IncidentProcessingSummary(
            actions=actions,
            state=state,
        )

    def _get_observed_at(self) -> datetime:
        """Read and normalize the monitoring observation time."""
        observed_at = self.clock()

        if not isinstance(observed_at, datetime):
            raise TypeError(
                "Incident pipeline clock must return a datetime."
            )

        if (
            observed_at.tzinfo is None
            or observed_at.utcoffset() is None
        ):
            raise ValueError(
                "Incident pipeline clock must return "
                "a timezone-aware datetime."
            )

        return observed_at.astimezone(timezone.utc)