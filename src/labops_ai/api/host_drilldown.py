"""Aggregate Host Registry and run-history drill-down data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    status,
)

from labops_ai.api.host_routes import (
    build_default_host_service,
)
from labops_ai.api.host_schemas import (
    HostDrilldownResponse,
    HostResponse,
)
from labops_ai.api.schemas import RunHistoryResponse
from labops_ai.health_status import HealthStatus
from labops_ai.history import RunHistoryQueryError
from labops_ai.hosts import (
    HostRegistryError,
    HostStatusSnapshot,
)


class HostStatusReader(Protocol):
    """Define Host Registry access required by drill-down."""

    def get_by_id(
        self,
        host_id: str,
    ) -> HostStatusSnapshot | None:
        """Return one Host status snapshot."""
        ...


class HostRunReader(Protocol):
    """Define run-history access required by drill-down."""

    def list_recent(
        self,
        *,
        limit: int,
        status: HealthStatus | None,
        host_name: str | None,
    ) -> list[RunHistoryResponse]:
        """Return recent monitoring runs."""
        ...


@dataclass(frozen=True, slots=True)
class HostDrilldownService:
    """Build a complete overview for one monitored Host."""

    host_reader: HostStatusReader
    run_reader: HostRunReader

    def __post_init__(self) -> None:
        """Validate injected readers."""
        if not callable(
            getattr(
                self.host_reader,
                "get_by_id",
                None,
            )
        ):
            raise TypeError(
                "host_reader must provide callable get_by_id."
            )

        if not callable(
            getattr(
                self.run_reader,
                "list_recent",
                None,
            )
        ):
            raise TypeError(
                "run_reader must provide callable list_recent."
            )

    def get_overview(
        self,
        *,
        host_id: str,
        limit: int,
    ) -> HostDrilldownResponse | None:
        """Return Host identity and its recent monitoring runs."""
        if not isinstance(host_id, str):
            raise TypeError("host_id must be a string.")

        normalized_host_id = host_id.strip()

        if not normalized_host_id:
            raise ValueError("host_id must not be empty.")

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer.")

        if not 1 <= limit <= 100:
            raise ValueError(
                "limit must be between 1 and 100."
            )

        snapshot = self.host_reader.get_by_id(
            normalized_host_id
        )

        if snapshot is None:
            return None

        host = HostResponse.from_snapshot(snapshot)

        runs = list(
            self.run_reader.list_recent(
                limit=limit,
                status=None,
                host_name=host.host_name,
            )
        )

        return HostDrilldownResponse(
            host=host,
            latest_run=runs[0] if runs else None,
            returned_run_count=len(runs),
            runs=runs,
        )


def _drilldown_unavailable(
    error: Exception,
) -> HTTPException:
    """Convert persistence failures into HTTP 503."""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Host drill-down data is temporarily "
            "unavailable."
        ),
    )


def build_host_drilldown_router(
    *,
    host_reader: HostStatusReader | None,
    run_reader: HostRunReader,
) -> APIRouter:
    """Build Host drill-down API routes."""
    resolved_host_reader = (
        host_reader
        if host_reader is not None
        else build_default_host_service()
    )

    service = HostDrilldownService(
        host_reader=resolved_host_reader,
        run_reader=run_reader,
    )

    router = APIRouter(
        prefix="/api/v1/hosts",
        tags=["hosts"],
    )

    @router.get(
        "/{host_id}/overview",
        response_model=HostDrilldownResponse,
    )
    def get_host_overview(
        host_id: str = Path(
            min_length=1,
            max_length=128,
        ),
        limit: int = Query(
            default=20,
            ge=1,
            le=100,
        ),
    ) -> HostDrilldownResponse:
        """Return one Host and its recent monitoring history."""
        try:
            result = service.get_overview(
                host_id=host_id,
                limit=limit,
            )
        except (
            HostRegistryError,
            RunHistoryQueryError,
        ) as error:
            raise _drilldown_unavailable(error) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {host_id} was not found.",
            )

        return result

    return router
