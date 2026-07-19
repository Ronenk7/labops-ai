"""Unit tests for persisted run history models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryEntry
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "history/history_models_cases.json"
)


def build_entry(
    **overrides: object,
) -> RunHistoryEntry:
    """Build one valid run history entry."""
    values: dict[str, object] = dict(
        CASES["valid_entry"]
    )
    values["generated_at"] = datetime.fromisoformat(
        str(values["generated_at"])
    )

    for field_name in (
        "overall_status",
        "system_status",
        "network_status",
        "service_status",
        "process_status",
        "log_status",
    ):
        values[field_name] = HealthStatus(
            str(values[field_name])
        )

    values.update(overrides)

    return RunHistoryEntry(**values)


class TestRunHistoryEntry:
    """Test one persisted monitoring run summary."""

    def test_accepts_and_normalizes_valid_entry(
        self,
    ) -> None:
        entry = build_entry(
            host_name="  Kukner7  ",
        )

        assert entry.run_id == 42
        assert entry.host_name == "Kukner7"
        assert entry.generated_at.isoformat() == (
            "2026-07-19T12:14:56+00:00"
        )
        assert entry.overall_status is HealthStatus.WARNING

    def test_returns_total_incident_count(self) -> None:
        entry = build_entry()

        assert entry.incident_count == 5

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_run_ids"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_run_id(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            build_entry(run_id=case["value"])

    def test_rejects_datetime_without_timezone(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="timezone information",
        ):
            build_entry(
                generated_at=datetime(
                    2026,
                    7,
                    19,
                    12,
                    14,
                    56,
                )
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_strings"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_required_string(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            build_entry(
                **{
                    case["field_name"]: case["value"]
                }
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_counts"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_incident_count(
        self,
        case: dict[str, Any],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            build_entry(
                **{
                    case["field_name"]: case["value"]
                }
            )

    def test_rejects_invalid_health_status(self) -> None:
        with pytest.raises(
            TypeError,
            match="HealthStatus",
        ):
            build_entry(
                overall_status=object(),
            )

    def test_rejects_non_zip_archive_path(self) -> None:
        with pytest.raises(
            ValueError,
            match=r"\.zip",
        ):
            build_entry(
                archive_path="runtime/report.json",
            )
