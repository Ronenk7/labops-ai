"""Unit tests for persistent JSON incident storage."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentDataError,
    IncidentRecord,
    IncidentSourceType,
    IncidentStatus,
    IncidentStorageConfig,
    IncidentStorageError,
    IncidentStoreState,
    JsonIncidentStore,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "incidents/incident_store_cases.json"
)


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 fixture datetime."""
    return datetime.fromisoformat(value)


def build_incident(
    case_name: str,
) -> IncidentRecord:
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


def build_store(path: Path) -> JsonIncidentStore:
    """Build an incident store using a temporary absolute path."""
    return JsonIncidentStore(
        config=IncidentStorageConfig(
            path=str(path)
        )
    )


class TestIncidentStoreState:
    """Test validation and querying of stored incident state."""

    def test_returns_active_and_resolved_incidents(self) -> None:
        active = build_incident("active_incident")
        resolved = build_incident("resolved_incident")
        state = IncidentStoreState(
            next_sequence=3,
            incidents=(active, resolved),
        )

        assert state.active_incidents == (active,)
        assert state.resolved_incidents == (resolved,)

    def test_finds_active_incident_case_insensitively(
        self,
    ) -> None:
        active = build_incident("active_incident")
        state = IncidentStoreState(
            next_sequence=2,
            incidents=(active,),
        )

        result = state.find_active(
            IncidentSourceType.SERVICE,
            "SYSTEMD-JOURNALD.SERVICE",
        )

        assert result == active

    def test_returns_none_when_active_incident_is_missing(
        self,
    ) -> None:
        state = IncidentStoreState(
            next_sequence=1,
            incidents=(),
        )

        result = state.find_active(
            IncidentSourceType.SYSTEM,
            "cpu",
        )

        assert result is None

    def test_rejects_duplicate_incident_ids(self) -> None:
        incident = build_incident("active_incident")

        with pytest.raises(
            ValueError,
            match="identifiers must be unique",
        ):
            IncidentStoreState(
                next_sequence=2,
                incidents=(incident, incident),
            )

    def test_rejects_duplicate_active_sources(self) -> None:
        first_incident = build_incident("active_incident")
        second_incident = replace(
            first_incident,
            incident_id="INC-000003",
        )

        with pytest.raises(
            ValueError,
            match="one active incident",
        ):
            IncidentStoreState(
                next_sequence=4,
                incidents=(
                    first_incident,
                    second_incident,
                ),
            )


class TestJsonIncidentStore:
    """Test persistent incident storage behavior."""

    def test_missing_file_returns_empty_state(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(
            tmp_path / "incidents.json"
        )

        state = store.load()

        assert state.next_sequence == 1
        assert state.incidents == ()

    def test_saves_and_loads_complete_state(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(
            tmp_path / "runtime" / "incidents.json"
        )
        expected_state = IncidentStoreState(
            next_sequence=3,
            incidents=(
                build_incident("active_incident"),
                build_incident("resolved_incident"),
            ),
        )

        store.save(expected_state)
        actual_state = store.load()

        assert actual_state == expected_state

    def test_saves_schema_and_sequence_information(
        self,
        tmp_path: Path,
    ) -> None:
        storage_path = tmp_path / "incidents.json"
        store = build_store(storage_path)
        state = IncidentStoreState(
            next_sequence=7,
            incidents=(),
        )

        store.save(state)

        payload = json.loads(
            storage_path.read_text(encoding="utf-8")
        )

        assert payload["schema_version"] == 1
        assert payload["next_sequence"] == 7
        assert payload["incidents"] == []

    def test_rejects_invalid_json(
        self,
        tmp_path: Path,
    ) -> None:
        storage_path = tmp_path / "incidents.json"
        storage_path.write_text(
            "{\"schema_version\":",
            encoding="utf-8",
        )

        with pytest.raises(
            IncidentDataError,
            match="invalid JSON",
        ):
            build_store(storage_path).load()

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_payloads"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_persisted_payload(
        self,
        tmp_path: Path,
        case: dict[str, Any],
    ) -> None:
        storage_path = tmp_path / "incidents.json"
        storage_path.write_text(
            json.dumps(case["payload"]),
            encoding="utf-8",
        )

        with pytest.raises(
            IncidentDataError,
            match=case["expected_message"],
        ):
            build_store(storage_path).load()

    def test_rejects_directory_as_storage_file(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(
            IncidentStorageError,
            match="could not be read",
        ):
            build_store(tmp_path).load()

    def test_rejects_invalid_state_dependency(
        self,
        tmp_path: Path,
    ) -> None:
        store = build_store(
            tmp_path / "incidents.json"
        )

        with pytest.raises(
            TypeError,
            match="IncidentStoreState",
        ):
            store.save(object())

    def test_reports_storage_write_failure(
        self,
        tmp_path: Path,
    ) -> None:
        blocked_parent = tmp_path / "blocked"
        blocked_parent.write_text(
            "This path is a file.",
            encoding="utf-8",
        )
        store = build_store(
            blocked_parent / "incidents.json"
        )
        state = IncidentStoreState(
            next_sequence=1,
            incidents=(),
        )

        with pytest.raises(
            IncidentStorageError,
            match="could not be written",
        ):
            store.save(state)