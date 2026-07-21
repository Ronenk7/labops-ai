"""Tests for remote diagnostic payload parsing."""
from __future__ import annotations

from copy import deepcopy

import pytest

from labops_ai.diagnostics import (
    DiagnosticPayloadError,
    parse_diagnostic_payload,
)
from labops_ai.health_status import HealthStatus
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit


def valid_payload() -> dict:
    """Return an isolated valid remote report."""
    return deepcopy(
        load_test_fixture(
            "diagnostics/remote_run_payload.json"
        )
    )


def test_parses_complete_remote_payload() -> None:
    """Rebuild the complete diagnostic domain."""
    snapshot = parse_diagnostic_payload(
        valid_payload()
    )

    assert snapshot.host_name == "lab-node-02"
    assert snapshot.overall_status is (
        HealthStatus.HEALTHY
    )
    assert len(snapshot.system_metrics) == 1
    assert len(snapshot.network_checks) == 1
    assert len(snapshot.services) == 1
    assert len(snapshot.processes) == 1
    assert len(snapshot.logs) == 1
    assert snapshot.incidents == ()


def test_rejects_unsupported_schema() -> None:
    """Reject unknown diagnostic formats."""
    payload = valid_payload()
    payload["schema_version"] = 999

    with pytest.raises(
        DiagnosticPayloadError,
        match="schema_version is unsupported",
    ):
        parse_diagnostic_payload(payload)


def test_rejects_inconsistent_summary() -> None:
    """Reject a summary that disagrees with details."""
    payload = valid_payload()
    payload["summary"]["network_status"] = (
        "CRITICAL"
    )

    with pytest.raises(
        DiagnosticPayloadError,
        match="summary.network_status",
    ):
        parse_diagnostic_payload(payload)
