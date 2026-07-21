"""Tests for the reusable complete monitoring runtime."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labops_ai.monitoring import runtime


pytestmark = pytest.mark.unit


def test_runs_complete_pipeline_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute every monitoring stage exactly once."""
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
    history_entry = object()

    def run_system_health():
        events.append("system")
        return (
            system_config,
            system_metrics,
            system_statuses,
        )

    def run_network_health():
        events.append("network")
        return network_summary

    def run_service_health():
        events.append("services")
        return service_summary

    def run_recovery_actions(summary):
        assert summary is service_summary
        events.append("recovery")
        return object()

    def run_process_health():
        events.append("processes")
        return process_summary

    def run_log_analysis():
        events.append("logs")
        return log_summary

    def run_incident_management(**arguments):
        assert arguments == {
            "system_config": system_config,
            "system_metrics": system_metrics,
            "system_statuses": system_statuses,
            "network_summary": network_summary,
            "service_summary": service_summary,
            "process_summary": process_summary,
            "log_summary": log_summary,
        }
        events.append("incidents")
        return SimpleNamespace(state=incident_state)

    def run_diagnostic_bundle(**arguments):
        assert arguments == {
            "system_config": system_config,
            "system_metrics": system_metrics,
            "system_statuses": system_statuses,
            "network_summary": network_summary,
            "service_summary": service_summary,
            "process_summary": process_summary,
            "log_summary": log_summary,
            "incident_state": incident_state,
        }
        events.append("diagnostics")
        return diagnostic_result

    def save_run_history(result):
        assert result is diagnostic_result
        events.append("history")
        return history_entry

    monkeypatch.setattr(
        runtime,
        "run_system_health",
        run_system_health,
    )
    monkeypatch.setattr(
        runtime,
        "run_network_health",
        run_network_health,
    )
    monkeypatch.setattr(
        runtime,
        "run_service_health",
        run_service_health,
    )
    monkeypatch.setattr(
        runtime,
        "run_recovery_actions",
        run_recovery_actions,
    )
    monkeypatch.setattr(
        runtime,
        "run_process_health",
        run_process_health,
    )
    monkeypatch.setattr(
        runtime,
        "run_log_analysis",
        run_log_analysis,
    )
    monkeypatch.setattr(
        runtime,
        "run_incident_management",
        run_incident_management,
    )
    monkeypatch.setattr(
        runtime,
        "run_diagnostic_bundle",
        run_diagnostic_bundle,
    )
    monkeypatch.setattr(
        runtime,
        "save_run_history",
        save_run_history,
    )

    result = runtime.run_complete_monitoring()

    assert result is history_entry
    assert events == [
        "system",
        "network",
        "services",
        "recovery",
        "processes",
        "logs",
        "incidents",
        "diagnostics",
        "history",
    ]


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
