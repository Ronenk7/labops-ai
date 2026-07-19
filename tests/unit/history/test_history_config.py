"""Unit tests for run history configuration models."""
from __future__ import annotations

from typing import Any

import pytest

from labops_ai.history import (
    RunHistoryConfig,
    RunHistoryRetentionConfig,
    RunHistoryStorageConfig,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "history/history_config_cases.json"
)


def build_storage() -> RunHistoryStorageConfig:
    """Build valid history storage configuration."""
    return RunHistoryStorageConfig(
        **CASES["valid_storage"]
    )


def build_retention() -> RunHistoryRetentionConfig:
    """Build valid history retention configuration."""
    return RunHistoryRetentionConfig(
        **CASES["valid_retention"]
    )


class TestRunHistoryStorageConfig:
    """Test SQLite storage settings."""

    def test_accepts_and_normalizes_valid_storage(
        self,
    ) -> None:
        config = RunHistoryStorageConfig(
            database_path=(
                "  runtime/run_history.sqlite3  "
            ),
            busy_timeout_seconds=5,
        )

        assert config.database_path == (
            "runtime/run_history.sqlite3"
        )
        assert config.busy_timeout_seconds == 5.0

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_database_paths"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_database_path(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_storage"])
        values["database_path"] = case["value"]

        with pytest.raises((TypeError, ValueError)):
            RunHistoryStorageConfig(**values)

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_timeouts"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_busy_timeout(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_storage"])
        values["busy_timeout_seconds"] = case["value"]

        with pytest.raises((TypeError, ValueError)):
            RunHistoryStorageConfig(**values)


class TestRunHistoryRetentionConfig:
    """Test automatic history retention settings."""

    def test_accepts_valid_retention(self) -> None:
        config = build_retention()

        assert config.max_runs == 1000
        assert config.max_age_days == 90
        assert config.prune_on_write is True

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_max_runs"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_max_runs(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_retention"])
        values["max_runs"] = case["value"]

        with pytest.raises((TypeError, ValueError)):
            RunHistoryRetentionConfig(**values)

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_max_age_days"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_max_age_days(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_retention"])
        values["max_age_days"] = case["value"]

        with pytest.raises((TypeError, ValueError)):
            RunHistoryRetentionConfig(**values)

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_prune_flags"],
        ids=lambda case: case["case_id"],
    )
    def test_rejects_invalid_prune_flag(
        self,
        case: dict[str, Any],
    ) -> None:
        values = dict(CASES["valid_retention"])
        values["prune_on_write"] = case["value"]

        with pytest.raises(TypeError, match="boolean"):
            RunHistoryRetentionConfig(**values)


class TestRunHistoryConfig:
    """Test the complete run history configuration."""

    def test_accepts_complete_configuration(self) -> None:
        config = RunHistoryConfig(
            storage=build_storage(),
            retention=build_retention(),
        )

        assert config.storage.database_path.endswith(
            ".sqlite3"
        )
        assert config.retention.max_runs == 1000

    def test_rejects_invalid_storage_model(self) -> None:
        with pytest.raises(
            TypeError,
            match="RunHistoryStorageConfig",
        ):
            RunHistoryConfig(
                storage=object(),
                retention=build_retention(),
            )
