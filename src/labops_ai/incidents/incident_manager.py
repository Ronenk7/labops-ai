"""Create, update, and resolve incidents from health signals."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Protocol

from labops_ai.health_status import HealthStatus
from labops_ai.incidents.incident_identifier import (
    IncidentIdGenerator,
)
from labops_ai.incidents.incident_models import (
    IncidentActionResult,
    IncidentActionType,
    IncidentRecord,
    IncidentSignal,
    IncidentStatus,
)
from labops_ai.incidents.incident_store import (
    IncidentStoreState,
)


class IncidentStore(Protocol):
    """Describe persistent storage required by the manager."""

    def load(self) -> IncidentStoreState:
        """Load the current incident state."""

    def save(self, state: IncidentStoreState) -> None:
        """Persist the supplied incident state."""


@dataclass(frozen=True, slots=True)
class IncidentManager:
    """Manage incident lifecycle changes from health signals."""

    store: IncidentStore
    id_generator: IncidentIdGenerator

    def __post_init__(self) -> None:
        """Validate storage and identifier dependencies."""
        if not callable(getattr(self.store, "load", None)):
            raise TypeError(
                "store must provide a callable load method."
            )

        if not callable(getattr(self.store, "save", None)):
            raise TypeError(
                "store must provide a callable save method."
            )

        if not isinstance(
            self.id_generator,
            IncidentIdGenerator,
        ):
            raise TypeError(
                "id_generator must be an "
                "IncidentIdGenerator instance."
            )

    def process_signal(
        self,
        signal: IncidentSignal,
    ) -> IncidentActionResult:
        """Process one health signal and persist any change."""
        if not isinstance(signal, IncidentSignal):
            raise TypeError(
                "signal must be an IncidentSignal instance."
            )

        return self.process_signals((signal,))[0]

    def process_signals(
        self,
        signals: Iterable[IncidentSignal],
    ) -> tuple[IncidentActionResult, ...]:
        """Process multiple signals using one storage transaction."""
        try:
            signal_collection = tuple(signals)
        except TypeError as error:
            raise TypeError(
                "signals must be an iterable of IncidentSignal "
                "instances."
            ) from error

        for signal in signal_collection:
            if not isinstance(signal, IncidentSignal):
                raise TypeError(
                    "Every signal must be an "
                    "IncidentSignal instance."
                )

        if not signal_collection:
            return ()

        state = self.store.load()

        if not isinstance(state, IncidentStoreState):
            raise TypeError(
                "Incident store must return "
                "an IncidentStoreState instance."
            )

        actions: list[IncidentActionResult] = []
        state_changed = False

        for signal in signal_collection:
            state, action = self._apply_signal(
                state=state,
                signal=signal,
            )
            actions.append(action)

            if (
                action.action_type
                is not IncidentActionType.UNCHANGED
            ):
                state_changed = True

        if state_changed:
            self.store.save(state)

        return tuple(actions)

    def _apply_signal(
        self,
        state: IncidentStoreState,
        signal: IncidentSignal,
    ) -> tuple[IncidentStoreState, IncidentActionResult]:
        """Apply one signal to an in-memory incident state."""
        active_incident = state.find_active(
            source_type=signal.source_type,
            source_id=signal.source_id,
        )

        if signal.severity is HealthStatus.HEALTHY:
            return self._apply_healthy_signal(
                state=state,
                signal=signal,
                active_incident=active_incident,
            )

        if active_incident is None:
            return self._create_incident(
                state=state,
                signal=signal,
            )

        return self._update_incident(
            state=state,
            signal=signal,
            active_incident=active_incident,
        )

    def _create_incident(
        self,
        state: IncidentStoreState,
        signal: IncidentSignal,
    ) -> tuple[IncidentStoreState, IncidentActionResult]:
        """Create a new active incident."""
        incident = IncidentRecord(
            incident_id=self.id_generator.generate(
                state.next_sequence
            ),
            source_type=signal.source_type,
            source_id=signal.source_id,
            source_label=signal.source_label,
            severity=signal.severity,
            status=IncidentStatus.OPEN,
            description=signal.description,
            first_seen_at=signal.observed_at,
            last_seen_at=signal.observed_at,
            occurrence_count=1,
        )

        updated_state = IncidentStoreState(
            next_sequence=state.next_sequence + 1,
            incidents=state.incidents + (incident,),
        )

        return (
            updated_state,
            IncidentActionResult(
                action_type=IncidentActionType.CREATED,
                signal=signal,
                incident=incident,
            ),
        )

    def _update_incident(
        self,
        state: IncidentStoreState,
        signal: IncidentSignal,
        active_incident: IncidentRecord,
    ) -> tuple[IncidentStoreState, IncidentActionResult]:
        """Update an existing active incident."""
        self._validate_signal_time(
            signal=signal,
            incident=active_incident,
        )

        severity = self._get_highest_severity(
            active_incident.severity,
            signal.severity,
        )

        updated_incident = replace(
            active_incident,
            source_label=signal.source_label,
            severity=severity,
            description=signal.description,
            last_seen_at=signal.observed_at,
            occurrence_count=(
                active_incident.occurrence_count + 1
            ),
        )

        updated_state = self._replace_incident(
            state=state,
            incident=updated_incident,
        )

        return (
            updated_state,
            IncidentActionResult(
                action_type=IncidentActionType.UPDATED,
                signal=signal,
                incident=updated_incident,
            ),
        )

    def _apply_healthy_signal(
        self,
        state: IncidentStoreState,
        signal: IncidentSignal,
        active_incident: IncidentRecord | None,
    ) -> tuple[IncidentStoreState, IncidentActionResult]:
        """Resolve an active incident or return unchanged."""
        if active_incident is None:
            return (
                state,
                IncidentActionResult(
                    action_type=IncidentActionType.UNCHANGED,
                    signal=signal,
                ),
            )

        self._validate_signal_time(
            signal=signal,
            incident=active_incident,
        )

        resolved_incident = replace(
            active_incident,
            status=IncidentStatus.RESOLVED,
            resolved_at=signal.observed_at,
        )

        updated_state = self._replace_incident(
            state=state,
            incident=resolved_incident,
        )

        return (
            updated_state,
            IncidentActionResult(
                action_type=IncidentActionType.RESOLVED,
                signal=signal,
                incident=resolved_incident,
            ),
        )

    @staticmethod
    def _replace_incident(
        state: IncidentStoreState,
        incident: IncidentRecord,
    ) -> IncidentStoreState:
        """Replace one stored incident by its identifier."""
        updated_incidents = tuple(
            incident
            if stored.incident_id == incident.incident_id
            else stored
            for stored in state.incidents
        )

        return IncidentStoreState(
            next_sequence=state.next_sequence,
            incidents=updated_incidents,
        )

    @staticmethod
    def _validate_signal_time(
        signal: IncidentSignal,
        incident: IncidentRecord,
    ) -> None:
        """Reject observations older than existing incident data."""
        if signal.observed_at < incident.last_seen_at:
            raise ValueError(
                "Incident signal observation time must not be "
                "earlier than the incident last seen time."
            )

    @staticmethod
    def _get_highest_severity(
        existing: HealthStatus,
        observed: HealthStatus,
    ) -> HealthStatus:
        """Preserve the highest severity reached by an incident."""
        if (
            existing is HealthStatus.CRITICAL
            or observed is HealthStatus.CRITICAL
        ):
            return HealthStatus.CRITICAL

        return HealthStatus.WARNING