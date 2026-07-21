"""Tests for the reusable monitoring runtime."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from labops_ai.monitoring import runtime


pytestmark = pytest.mark.unit


def test_runs_complete_diagnostics_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute every diagnostic stage once."""
    events: list[str] = []

    system_config = object()
    system_metrics = {"cpu": 10.0}
    system_statuses = {"cpu": object()}
    network_summary = object()
    service_summary = object()
    process_summary = object()
    log_summary = object()
    incident_state = object()
    diagnostic_result = object()

    monkeypatch.setattr(
        runtime,
        "run_system_health",
        lambda: (
            events.append("system")
            or (
                system_config,
                system_metrics,
                system_statuses,
            )
        ),
    )
    monkeypatch.setattr(
        runtime,
        "run_network_health",
        lambda: (
            events.append("network")
            or network_summary
        ),
    )
    monkeypatch.setattr(
        runtime,
        "run_service_health",
        lambda: (
            events.append("services")
            or service_summary
        ),
    )

    def recovery(summary):
        assert summary is service_summary
        events.append("recovery")

    monkeypatch.setattr(
        runtime,
        "run_recovery_actions",
        recovery,
    )
    monkeypatch.setattr(
        runtime,
        "run_process_health",
        lambda: (
            events.append("processes")
            or process_summary
        ),
    )
    monkeypatch.setattr(
        runtime,
        "run_log_analysis",
        lambda: (
            events.append("logs")
            or log_summary
        ),
    )

    def incidents(**arguments):
        assert arguments["system_config"] is (
            system_config
        )
        events.append("incidents")
        return SimpleNamespace(
            state=incident_state
        )

    monkeypatch.setattr(
        runtime,
        "run_incident_management",
        incidents,
    )

    def diagnostics(**arguments):
        assert arguments["incident_state"] is (
            incident_state
        )
        events.append("diagnostics")
        return diagnostic_result

    monkeypatch.setattr(
        runtime,
        "run_diagnostic_bundle",
        diagnostics,
    )

    result = runtime.run_complete_diagnostics()

    assert result is diagnostic_result
    assert events == [
        "system",
        "network",
        "services",
        "recovery",
        "processes",
        "logs",
        "incidents",
        "diagnostics",
    ]


def test_remote_runtime_removes_local_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return the snapshot without local history."""
    archive_path = (
        tmp_path / "remote-run.zip"
    )
    archive_path.write_bytes(b"temporary")

    snapshot = object()
    result = SimpleNamespace(
        snapshot=snapshot,
        bundle=SimpleNamespace(
            archive_path=archive_path
        ),
    )

    monkeypatch.setattr(
        runtime,
        "run_complete_diagnostics",
        lambda: result,
    )

    returned = (
        runtime.run_remote_monitoring_snapshot()
    )

    assert returned is snapshot
    assert not archive_path.exists()


def test_complete_monitoring_saves_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persist diagnostics for local execution."""
    diagnostic_result = object()
    history_entry = object()

    monkeypatch.setattr(
        runtime,
        "run_complete_diagnostics",
        lambda: diagnostic_result,
    )
    monkeypatch.setattr(
        runtime,
        "save_run_history",
        lambda result: (
            history_entry
            if result is diagnostic_result
            else None
        ),
    )

    result = runtime.run_complete_monitoring()

    assert result is history_entry


def test_command_entry_point_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep python -m labops_ai behavior intact."""
    import labops_ai.__main__ as command

    calls: list[str] = []

    monkeypatch.setattr(
        command,
        "run_complete_monitoring",
        lambda: calls.append("run"),
    )

    command.main()

    assert calls == ["run"]
