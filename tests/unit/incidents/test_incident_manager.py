"""Unit tests for incident lifecycle management."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentActionType,
    IncidentIdGenerator,
    IncidentIdentifierConfig,
    IncidentManager,
    IncidentRecord,
    IncidentSignal,
    IncidentSourceType,
    IncidentStatus,
    IncidentStoreState,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_manager_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse one ISO 8601 fixture timestamp."""
    return datetime.fromisoformat(value)


def build_signal(case_name: str) -> IncidentSignal:
    """Build one incident signal from external test data."""
    case = CASES[case_name]

    return IncidentSignal(
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        description=case["description"],
        observed_at=parse_datetime(case["observed_at"]),
    )


def build_incident(case_name: str) -> IncidentRecord:
    """Build one incident record from external test data."""
    case = CASES[case_name]

    return IncidentRecord(
        incident_id=case["incident_id"],
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        status=IncidentStatus(case["status"]),
        description=case["description"],
        first_seen_at=parse_datetime(case["first_seen_at"]),
        last_seen_at=parse_datetime(case["last_seen_at"]),
        occurrence_count=case["occurrence_count"],
        resolved_at=(
            parse_datetime(case["resolved_at"])
            if case["resolved_at"] is not None
            else None
        ),
    )


def build_generator() -> IncidentIdGenerator:
    """Build the configured incident ID generator."""
    return IncidentIdGenerator(
        config=IncidentIdentifierConfig(
            **CASES["identifier"]
        )
    )


@dataclass
class FakeIncidentStore:
    """Store controlled incident state in memory."""

    state: IncidentStoreState
    saved_states: list[IncidentStoreState] = field(
        default_factory=list
    )

    def load(self) -> IncidentStoreState:
        """Return the current controlled state."""
        return self.state

    def save(self, state: IncidentStoreState) -> None:
        """Record and retain the supplied state."""
        self.saved_states.append(state)
        self.state = state


def build_manager(
    state: IncidentStoreState,
) -> tuple[IncidentManager, FakeIncidentStore]:
    """Build a manager and its in-memory store."""
    store = FakeIncidentStore(state=state)
    manager = IncidentManager(
        store=store,
        id_generator=build_generator(),
    )
    return manager, store


class TestIncidentManager:
    """Test incident creation, updates, and resolution."""

    def test_creates_incident_for_warning_signal(self) -> None:
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        action = manager.process_signal(
            build_signal("warning_signal")
        )

        assert action.action_type is IncidentActionType.CREATED
        assert action.incident is not None
        assert action.incident.incident_id == "INC-000001"
        assert action.incident.status is IncidentStatus.OPEN
        assert action.incident.occurrence_count == 1
        assert store.state.next_sequence == 2
        assert len(store.saved_states) == 1

    def test_updates_existing_active_incident(self) -> None:
        incident = build_incident(
            "active_warning_incident"
        )
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )

        action = manager.process_signal(
            build_signal("warning_signal")
        )

        assert action.action_type is IncidentActionType.UPDATED
        assert action.incident is not None
        assert action.incident.occurrence_count == 2
        assert action.incident.description == (
            "Service is transitioning."
        )
        assert len(store.saved_states) == 1

    def test_escalates_warning_incident_to_critical(
        self,
    ) -> None:
        incident = build_incident(
            "active_warning_incident"
        )
        manager, _ = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )

        action = manager.process_signal(
            build_signal("critical_signal")
        )

        assert action.incident is not None
        assert (
            action.incident.severity
            is HealthStatus.CRITICAL
        )
        assert action.incident.occurrence_count == 2

    def test_does_not_downgrade_critical_incident(
        self,
    ) -> None:
        incident = build_incident(
            "active_critical_incident"
        )
        manager, _ = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )

        action = manager.process_signal(
            build_signal("later_warning_signal")
        )

        assert action.incident is not None
        assert (
            action.incident.severity
            is HealthStatus.CRITICAL
        )
        assert action.incident.occurrence_count == 3

    def test_preserves_acknowledged_status_on_update(
        self,
    ) -> None:
        incident = build_incident(
            "acknowledged_incident"
        )
        manager, _ = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )

        action = manager.process_signal(
            build_signal("warning_signal")
        )

        assert action.incident is not None
        assert (
            action.incident.status
            is IncidentStatus.ACKNOWLEDGED
        )

    def test_resolves_active_incident_for_healthy_signal(
        self,
    ) -> None:
        incident = build_incident(
            "active_critical_incident"
        )
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )

        action = manager.process_signal(
            build_signal("healthy_signal")
        )

        assert action.action_type is IncidentActionType.RESOLVED
        assert action.incident is not None
        assert (
            action.incident.status
            is IncidentStatus.RESOLVED
        )
        assert action.incident.resolved_at == parse_datetime(
            CASES["healthy_signal"]["observed_at"]
        )
        assert store.state.active_incidents == ()
        assert len(store.state.resolved_incidents) == 1

    def test_healthy_signal_without_incident_is_unchanged(
        self,
    ) -> None:
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        action = manager.process_signal(
            build_signal("healthy_signal")
        )

        assert (
            action.action_type
            is IncidentActionType.UNCHANGED
        )
        assert action.incident is None
        assert store.saved_states == []

    def test_processes_multiple_signals_with_one_save(
        self,
    ) -> None:
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        actions = manager.process_signals(
            (
                build_signal("warning_signal"),
                build_signal("network_warning_signal"),
            )
        )

        assert [
            action.incident.incident_id
            for action in actions
            if action.incident is not None
        ] == [
            "INC-000001",
            "INC-000002",
        ]
        assert store.state.next_sequence == 3
        assert len(store.state.active_incidents) == 2
        assert len(store.saved_states) == 1

    def test_rejects_signal_older_than_incident(
        self,
    ) -> None:
        incident = build_incident(
            "active_warning_incident"
        )
        manager, store = build_manager(
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident,),
            )
        )
        old_signal = replace(
            build_signal("warning_signal"),
            observed_at=parse_datetime(
                "2026-07-19T09:59:00+00:00"
            ),
        )

        with pytest.raises(
            ValueError,
            match="earlier than",
        ):
            manager.process_signal(old_signal)

        assert store.saved_states == []

    def test_rejects_invalid_store_dependency(self) -> None:
        with pytest.raises(
            TypeError,
            match="load method",
        ):
            IncidentManager(
                store=object(),
                id_generator=build_generator(),
            )

    def test_rejects_invalid_identifier_generator(
        self,
    ) -> None:
        store = FakeIncidentStore(
            state=IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        with pytest.raises(
            TypeError,
            match="IncidentIdGenerator",
        ):
            IncidentManager(
                store=store,
                id_generator=object(),
            )

    def test_rejects_invalid_state_from_store(self) -> None:
        @dataclass
        class InvalidStateStore:
            """Return an invalid state object."""

            def load(self) -> object:
                return object()

            def save(self, state: IncidentStoreState) -> None:
                pass

        manager = IncidentManager(
            store=InvalidStateStore(),
            id_generator=build_generator(),
        )

        with pytest.raises(
            TypeError,
            match="IncidentStoreState",
        ):
            manager.process_signal(
                build_signal("warning_signal")
            )

    def test_rejects_invalid_signal(self) -> None:
        manager, _ = build_manager(
            IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        with pytest.raises(
            TypeError,
            match="IncidentSignal",
        ):
            manager.process_signal(object())