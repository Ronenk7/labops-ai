"""Unit tests for Linux service health reports."""
from __future__ import annotations

import pytest

from labops_ai.health_status import HealthStatus
from labops_ai.services import (
    ServiceCheckResult,
    ServiceCheckStatus,
    ServiceHealthRecord,
    ServiceMonitoringSummary,
    ServiceReportConfig,
    build_service_report,
    print_service_report,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "services/service_report_cases.json"
)
REPORT = ServiceReportConfig(**CASES["report"])


def build_summary() -> ServiceMonitoringSummary:
    """Build a report summary from controlled test values."""
    active_result = ServiceCheckResult(
        service_name="cron.service",
        label="Cron Scheduler",
        status=ServiceCheckStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="running",
    )
    failed_result = ServiceCheckResult(
        service_name="ssh.service",
        label="SSH Server",
        status=ServiceCheckStatus.FAILED,
        load_state="loaded",
        active_state="failed",
        sub_state="failed",
    )

    return ServiceMonitoringSummary(
        records=(
            ServiceHealthRecord(
                result=active_result,
                health_status=HealthStatus.HEALTHY,
            ),
            ServiceHealthRecord(
                result=failed_result,
                health_status=HealthStatus.CRITICAL,
            ),
        ),
        overall_status=HealthStatus.CRITICAL,
    )


class TestBuildServiceReport:
    """Test human-readable service report construction."""

    def test_builds_complete_service_report(self) -> None:
        actual_report = build_service_report(
            summary=build_summary(),
            report=REPORT,
        )

        assert actual_report == CASES["expected_report"]

    def test_rejects_invalid_summary(self) -> None:
        with pytest.raises(
            TypeError,
            match="ServiceMonitoringSummary",
        ):
            build_service_report(
                summary=object(),
                report=REPORT,
            )


class TestPrintServiceReport:
    """Test printing service reports."""

    def test_prints_complete_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        print_service_report(
            summary=build_summary(),
            report=REPORT,
        )

        captured = capsys.readouterr()

        assert captured.out == f'{CASES["expected_report"]}\n'
        assert captured.err == ""