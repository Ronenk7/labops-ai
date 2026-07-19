"""Calculate dashboard analytics from run history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from labops_ai.api.contracts import RunHistoryReader
from labops_ai.api.schemas import (
    ComponentReliabilityResponse,
    DashboardOverviewResponse,
    DashboardTrendPointResponse,
    RunHistoryResponse,
    StatusDistributionResponse,
)
from labops_ai.health_status import HealthStatus


_MAX_ANALYTICS_LIMIT = 200


def _healthy_percentage(
    statuses: tuple[HealthStatus, ...],
) -> float:
    """Return the healthy percentage for one collection."""
    if not statuses:
        return 0.0

    healthy_count = sum(
        status is HealthStatus.HEALTHY
        for status in statuses
    )

    return round(
        healthy_count / len(statuses) * 100,
        1,
    )


@dataclass(frozen=True, slots=True)
class DashboardAnalyticsService:
    """Build aggregated dashboard information."""

    reader: RunHistoryReader

    def __post_init__(self) -> None:
        """Validate the history reader dependency."""
        if not callable(
            getattr(self.reader, "list_recent", None)
        ):
            raise TypeError(
                "reader must provide callable list_recent."
            )

    def build_overview(
        self,
        *,
        limit: int = 100,
        host_name: str | None = None,
    ) -> DashboardOverviewResponse:
        """Calculate one dashboard overview response."""
        if isinstance(limit, bool) or not isinstance(
            limit,
            int,
        ):
            raise TypeError(
                "Dashboard analytics limit must be an integer."
            )

        if not 1 <= limit <= _MAX_ANALYTICS_LIMIT:
            raise ValueError(
                "Dashboard analytics limit must be "
                f"between 1 and {_MAX_ANALYTICS_LIMIT}."
            )

        entries = self.reader.list_recent(
            limit=limit,
            status=None,
            host_name=host_name,
        )

        healthy_count = sum(
            entry.overall_status is HealthStatus.HEALTHY
            for entry in entries
        )
        warning_count = sum(
            entry.overall_status is HealthStatus.WARNING
            for entry in entries
        )
        critical_count = sum(
            entry.overall_status is HealthStatus.CRITICAL
            for entry in entries
        )

        healthy_streak = 0

        for entry in entries:
            if (
                entry.overall_status
                is not HealthStatus.HEALTHY
            ):
                break

            healthy_streak += 1

        latest_run = (
            RunHistoryResponse.from_entry(entries[0])
            if entries
            else None
        )

        return DashboardOverviewResponse(
            generated_at=datetime.now(timezone.utc),
            sample_size=len(entries),
            health_score=_healthy_percentage(
                tuple(
                    entry.overall_status
                    for entry in entries
                )
            ),
            active_incident_total=sum(
                entry.active_incident_count
                for entry in entries
            ),
            current_healthy_streak=healthy_streak,
            hosts=sorted(
                {
                    entry.host_name
                    for entry in entries
                }
            ),
            latest_run=latest_run,
            status_distribution=(
                StatusDistributionResponse(
                    healthy=healthy_count,
                    warning=warning_count,
                    critical=critical_count,
                )
            ),
            component_reliability=(
                ComponentReliabilityResponse(
                    system=_healthy_percentage(
                        tuple(
                            entry.system_status
                            for entry in entries
                        )
                    ),
                    network=_healthy_percentage(
                        tuple(
                            entry.network_status
                            for entry in entries
                        )
                    ),
                    services=_healthy_percentage(
                        tuple(
                            entry.service_status
                            for entry in entries
                        )
                    ),
                    processes=_healthy_percentage(
                        tuple(
                            entry.process_status
                            for entry in entries
                        )
                    ),
                    logs=_healthy_percentage(
                        tuple(
                            entry.log_status
                            for entry in entries
                        )
                    ),
                )
            ),
            trend=[
                DashboardTrendPointResponse(
                    run_id=entry.run_id,
                    generated_at=entry.generated_at,
                    status=entry.overall_status,
                    active_incidents=(
                        entry.active_incident_count
                    ),
                )
                for entry in reversed(entries)
            ],
        )
