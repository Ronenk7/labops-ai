"""Create the read-only LabOps AI FastAPI application."""
from __future__ import annotations

from typing import Annotated

from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Query,
    status as http_status,
)

from labops_ai.api.schemas import (
    ApiHealthResponse,
    RunHistoryResponse,
)
from labops_ai.api.service import (
    RunHistoryApiService,
)
from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryConfigLoader,
    RunHistoryDatabase,
    RunHistoryQuery,
    RunHistoryQueryError,
)


API_VERSION = "0.1.0"


def build_default_history_service(
) -> RunHistoryApiService:
    """Build the production SQLite history service."""
    config = RunHistoryConfigLoader().load()
    database = RunHistoryDatabase(
        config=config.storage
    )
    query = RunHistoryQuery(database=database)

    return RunHistoryApiService(reader=query)


def _normalize_host_name(
    host_name: str | None,
) -> str | None:
    """Normalize an optional API host filter."""
    if host_name is None:
        return None

    normalized = host_name.strip()

    if not normalized:
        raise HTTPException(
            status_code=(
                http_status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail="host_name must not be empty.",
        )

    return normalized


def _history_unavailable(
    error: RunHistoryQueryError,
) -> HTTPException:
    """Convert storage failures into HTTP 503."""
    return HTTPException(
        status_code=(
            http_status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        detail="Run history is temporarily unavailable.",
    )


def create_app(
    history_service: RunHistoryApiService | None = None,
) -> FastAPI:
    """Create an API with injectable history access."""
    service = (
        history_service
        if history_service is not None
        else build_default_history_service()
    )

    if not isinstance(
        service,
        RunHistoryApiService,
    ):
        raise TypeError(
            "history_service must be a "
            "RunHistoryApiService."
        )

    application = FastAPI(
        title="LabOps AI API",
        description=(
            "Read-only monitoring, incident, "
            "and diagnostic history API."
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @application.get(
        "/api/v1/health",
        response_model=ApiHealthResponse,
        tags=["system"],
    )
    def get_api_health() -> ApiHealthResponse:
        """Return API process availability."""
        return ApiHealthResponse(
            service="LabOps AI API",
            status=HealthStatus.HEALTHY,
            version=API_VERSION,
        )

    @application.get(
        "/api/v1/runs/latest",
        response_model=RunHistoryResponse,
        tags=["runs"],
    )
    def get_latest_run(
        host_name: Annotated[
            str | None,
            Query(
                min_length=1,
                max_length=255,
            ),
        ] = None,
    ) -> RunHistoryResponse:
        """Return the newest stored monitoring run."""
        normalized_host = _normalize_host_name(
            host_name
        )

        try:
            result = service.get_latest(
                host_name=normalized_host
            )
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

        if result is None:
            raise HTTPException(
                status_code=(
                    http_status.HTTP_404_NOT_FOUND
                ),
                detail="No monitoring run was found.",
            )

        return result

    @application.get(
        "/api/v1/runs",
        response_model=list[RunHistoryResponse],
        tags=["runs"],
    )
    def list_runs(
        limit: Annotated[
            int,
            Query(ge=1, le=100),
        ] = 20,
        health_status: Annotated[
            HealthStatus | None,
            Query(alias="status"),
        ] = None,
        host_name: Annotated[
            str | None,
            Query(
                min_length=1,
                max_length=255,
            ),
        ] = None,
    ) -> list[RunHistoryResponse]:
        """Return recent runs with optional filters."""
        normalized_host = _normalize_host_name(
            host_name
        )

        try:
            return service.list_recent(
                limit=limit,
                status=health_status,
                host_name=normalized_host,
            )
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

    @application.get(
        "/api/v1/runs/{run_id}",
        response_model=RunHistoryResponse,
        tags=["runs"],
    )
    def get_run_by_id(
        run_id: Annotated[
            int,
            Path(ge=1),
        ],
    ) -> RunHistoryResponse:
        """Return one monitoring run by identifier."""
        try:
            result = service.get_by_id(run_id)
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

        if result is None:
            raise HTTPException(
                status_code=(
                    http_status.HTTP_404_NOT_FOUND
                ),
                detail=(
                    f"Monitoring run {run_id} "
                    "was not found."
                ),
            )

        return result

    return application


app = create_app()
