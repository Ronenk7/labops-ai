"""Unit tests for system health configuration models."""
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from labops_ai.config.system_health_config import (
    HealthThresholds,
    SystemHealthCollectionConfig,
    SystemHealthConfig,
    SystemHealthReportConfig,
)
from tests.support.fixture_loader import load_test_fixture


CASES = load_test_fixture("system_health/system_health_config_cases.json")


def build_system_health_config(
    configuration: dict[str, Any],
) -> SystemHealthConfig:
    """Build a validated system health configuration from fixture data."""
    return SystemHealthConfig(
        collection=SystemHealthCollectionConfig(**configuration["collection"]),
        metric_thresholds={
            metric_name: HealthThresholds(**threshold_values)
            for metric_name, threshold_values in configuration["metrics"].items()
        },
        report=SystemHealthReportConfig(**configuration["report"]),
    )


@pytest.mark.unit
class TestHealthThresholds:
    """Verify threshold validation and immutability."""

    @pytest.mark.parametrize(
        "case",
        CASES["valid_thresholds"],
        ids=lambda case: case["id"],
    )
    def test_accepts_valid_thresholds(self, case: dict[str, Any]) -> None:
        """Verify that valid external threshold values are accepted."""
        thresholds = HealthThresholds(
            warning=case["warning"],
            critical=case["critical"],
        )

        assert thresholds.warning == float(case["warning"])
        assert thresholds.critical == float(case["critical"])

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_threshold_ranges"],
        ids=lambda case: case["id"],
    )
    def test_rejects_thresholds_outside_percentage_range(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that percentages outside the supported range fail."""
        with pytest.raises(ValueError):
            HealthThresholds(
                warning=case["warning"],
                critical=case["critical"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_threshold_order"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_threshold_order(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that warning must remain lower than critical."""
        with pytest.raises(
            ValueError,
            match="Warning threshold must be lower",
        ):
            HealthThresholds(
                warning=case["warning"],
                critical=case["critical"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_threshold_types"],
        ids=lambda case: case["id"],
    )
    def test_rejects_non_numeric_thresholds(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that threshold values accept only numeric types."""
        with pytest.raises(TypeError):
            HealthThresholds(
                warning=case["warning"],
                critical=case["critical"],
            )

    def test_thresholds_are_immutable(self) -> None:
        """Verify that validated thresholds cannot be mutated."""
        case = CASES["immutable_thresholds"]
        thresholds = HealthThresholds(
            warning=case["warning"],
            critical=case["critical"],
        )

        with pytest.raises(FrozenInstanceError):
            setattr(
                thresholds,
                "warning",
                case["replacement_warning"],
            )


@pytest.mark.unit
class TestSystemHealthCollectionConfig:
    """Verify system metric collection configuration validation."""

    def test_accepts_valid_collection_settings(self) -> None:
        """Verify that valid external collection settings are normalized."""
        case = CASES["valid_collection"]
        config = SystemHealthCollectionConfig(**case)

        assert config.cpu_sample_interval_seconds == float(
            case["cpu_sample_interval_seconds"]
        )
        assert config.disk_mount_point == case["disk_mount_point"]

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_collection_intervals"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_cpu_sample_intervals(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that invalid sample intervals fail validation."""
        valid_case = CASES["valid_collection"]

        expected_error = (
            TypeError
            if isinstance(case["value"], (str, bool)) or case["value"] is None
            else ValueError
        )

        with pytest.raises(expected_error):
            SystemHealthCollectionConfig(
                cpu_sample_interval_seconds=case["value"],
                disk_mount_point=valid_case["disk_mount_point"],
            )

    @pytest.mark.parametrize(
        "case",
        CASES["invalid_mount_points"],
        ids=lambda case: case["id"],
    )
    def test_rejects_invalid_disk_mount_points(
        self,
        case: dict[str, Any],
    ) -> None:
        """Verify that invalid disk mount points fail validation."""
        valid_case = CASES["valid_collection"]

        expected_error = (
            TypeError
            if not isinstance(case["value"], str)
            else ValueError
        )

        with pytest.raises(expected_error):
            SystemHealthCollectionConfig(
                cpu_sample_interval_seconds=valid_case[
                    "cpu_sample_interval_seconds"
                ],
                disk_mount_point=case["value"],
            )


@pytest.mark.unit
class TestSystemHealthConfig:
    """Verify complete system health configuration consistency."""

    def test_creates_complete_system_health_configuration(self) -> None:
        """Verify that complete external configuration creates all models."""
        configuration = CASES["valid_system_config"]
        config = build_system_health_config(configuration)

        assert set(config.metric_thresholds) == set(configuration["metrics"])
        assert dict(config.report.metric_labels) == configuration["report"][
            "metric_labels"
        ]

    def test_rejects_missing_metric_threshold(self) -> None:
        """Verify that every supported metric must define thresholds."""
        configuration = CASES["valid_system_config"]

        thresholds = {
            metric_name: HealthThresholds(**threshold_values)
            for metric_name, threshold_values in configuration["metrics"].items()
        }

        thresholds.pop(next(iter(thresholds)))

        with pytest.raises(
            ValueError,
            match="must define every supported metric",
        ):
            SystemHealthConfig(
                collection=SystemHealthCollectionConfig(
                    **configuration["collection"]
                ),
                metric_thresholds=thresholds,
                report=SystemHealthReportConfig(
                    **configuration["report"]
                ),
            )