"""Unit tests for complete incident processing orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentActionResult,
    IncidentIdGenerator,
    IncidentIdentifierConfig,
    IncidentManager,
    IncidentPipeline,
    IncidentProcessingSummary,
    IncidentSignal,
    IncidentSourceType,
    IncidentStoreState,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_pipeline_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse one ISO 8601 test timestamp."""
    return datetime.fromisoformat(value)


def build_signal(
    case_name: str,
    observed_at: datetime,
) -> IncidentSignal:
    """Build one pipeline signal from external fixture data."""
    case = CASES[case_name]

    return IncidentSignal(
        source_type=IncidentSourceType(case["source_type"]),
        source_id=case["source_id"],
        source_label=case["source_label"],
        severity=HealthStatus(case["severity"]),
        description=case["description"],
        observed_at=observed_at,
    )


@dataclass
class FakeIncidentStore:
    """Keep incident state in memory for pipeline tests."""

    state: IncidentStoreState
    load_count: int = 0
    saved_states: list[IncidentStoreState] = field(
        default_factory=list
    )

    def load(self) -> IncidentStoreState:
        """Return the controlled state."""
        self.load_count += 1
        return self.state

    def save(self, state: IncidentStoreState) -> None:
        """Record and retain the updated state."""
        self.saved_states.append(state)
        self.state = state


@dataclass
class FakeSignalFactory:
    """Create controlled signals and capture pipeline input."""

    received: dict[str, Any] | None = None

    def from_all(self, **values: Any) -> tuple[IncidentSignal, ...]:
        """Return controlled signals using the supplied timestamp."""
        self.received = values
        observed_at = values["observed_at"]

        return (
            build_signal("warning_signal", observed_at),
            build_signal("healthy_signal", observed_at),
        )


def build_manager(
    store: FakeIncidentStore,
) -> IncidentManager:
    """Build a real incident manager using fake storage."""
    return IncidentManager(
        store=store,
        id_generator=IncidentIdGenerator(
            config=IncidentIdentifierConfig(
                prefix="INC",
                separator="-",
                sequence_width=6,
            )
        ),
    )


def build_pipeline(
    clock=lambda: parse_datetime(CASES["observed_at"]),
) -> tuple[
    IncidentPipeline,
    FakeIncidentStore,
    FakeSignalFactory,
]:
    """Build a pipeline and its controlled dependencies."""
    store = FakeIncidentStore(
        state=IncidentStoreState(
            next_sequence=1,
            incidents=(),
        )
    )
    factory = FakeSignalFactory()
    pipeline = IncidentPipeline(
        signal_factory=factory,
        manager=build_manager(store),
        clock=clock,
    )

    return pipeline, store, factory


def run_pipeline(
    pipeline: IncidentPipeline,
) -> IncidentProcessingSummary:
    """Run the pipeline with controlled monitoring objects."""
    return pipeline.run(
        system_metrics={"cpu_percent": 10.0},
        system_statuses={
            "cpu_percent": HealthStatus.HEALTHY
        },
        system_metric_labels={"cpu_percent": "CPU usage"},
        network_summary=object(),
        service_summary=object(),
        process_summary=object(),
        log_summary=object(),
    )


class TestIncidentProcessingSummary:
    """Test complete pipeline result validation."""

    def test_accepts_valid_empty_result(self) -> None:
        summary = IncidentProcessingSummary(
            actions=(),
            state=IncidentStoreState(
                next_sequence=1,
                incidents=(),
            ),
        )

        assert summary.actions == ()
        assert summary.state.incidents == ()

    def test_rejects_non_tuple_actions(self) -> None:
        with pytest.raises(
            TypeError,
            match="actions must be a tuple",
        ):
            IncidentProcessingSummary(
                actions=[],
                state=IncidentStoreState(
                    next_sequence=1,
                    incidents=(),
                ),
            )


class TestIncidentPipeline:
    """Test full incident pipeline orchestration."""

    def test_processes_signals_and_returns_persisted_state(
        self,
    ) -> None:
        pipeline, store, _ = build_pipeline()

        summary = run_pipeline(pipeline)

        assert len(summary.actions) == 2
        assert len(summary.state.active_incidents) == 1
        assert (
            summary.state.active_incidents[0].incident_id
            == "INC-000001"
        )
        assert len(store.saved_states) == 1
        assert store.load_count == 2

    def test_passes_monitoring_data_and_utc_time_to_factory(
        self,
    ) -> None:
        pipeline, _, factory = build_pipeline()

        run_pipeline(pipeline)

        assert factory.received is not None
        assert factory.received["system_metrics"] == {
            "cpu_percent": 10.0
        }
        assert factory.received["observed_at"] == (
            parse_datetime(CASES["observed_at"])
            .astimezone(timezone.utc)
        )

    def test_rejects_invalid_signal_factory(self) -> None:
        store = FakeIncidentStore(
            state=IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        with pytest.raises(
            TypeError,
            match="from_all method",
        ):
            IncidentPipeline(
                signal_factory=object(),
                manager=build_manager(store),
            )

    def test_rejects_invalid_manager(self) -> None:
        with pytest.raises(
            TypeError,
            match="IncidentManager",
        ):
            IncidentPipeline(
                signal_factory=FakeSignalFactory(),
                manager=object(),
            )

    def test_rejects_non_callable_clock(self) -> None:
        store = FakeIncidentStore(
            state=IncidentStoreState(
                next_sequence=1,
                incidents=(),
            )
        )

        with pytest.raises(
            TypeError,
            match="clock must be callable",
        ):
            IncidentPipeline(
                signal_factory=FakeSignalFactory(),
                manager=build_manager(store),
                clock=object(),
            )

    def test_rejects_naive_clock_result(self) -> None:
        pipeline, _, _ = build_pipeline(
            clock=lambda: datetime(2026, 7, 19, 13, 30)
        )

        with pytest.raises(
            ValueError,
            match="timezone-aware",
        ):
            run_pipeline(pipeline)