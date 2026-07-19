"""Create the LabOps AI monitoring and reporting API."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import (
    FastAPI,
    HTTPException,
    Path as ApiPath,
    Query,
    status as http_status,
)
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles

from labops_ai.api.analytics import (
    DashboardAnalyticsService,
)
from labops_ai.api.incident_service import (
    IncidentApiService,
)
from labops_ai.api.reporting import (
    RunHistoryCsvReportBuilder,
)
from labops_ai.api.schemas import (
    ApiHealthResponse,
    DashboardOverviewResponse,
    IncidentResponse,
    IncidentSummaryResponse,
    RunHistoryResponse,
)
from labops_ai.api.service import RunHistoryApiService
from labops_ai.health_status import HealthStatus
from labops_ai.history import (
    RunHistoryConfigLoader,
    RunHistoryDatabase,
    RunHistoryQuery,
    RunHistoryQueryError,
)
from labops_ai.incidents import (
    IncidentManagementConfigLoader,
    IncidentSourceType,
    IncidentStatus,
    IncidentStorageError,
    JsonIncidentStore,
)


API_VERSION = "0.3.0"
DASHBOARD_DIRECTORY = FilePath(__file__).with_name(
    "dashboard"
)
DASHBOARD_FILE = DASHBOARD_DIRECTORY / "index.html"
DASHBOARD_STATIC_DIRECTORY = (
    DASHBOARD_DIRECTORY / "static"
)


def build_default_history_service(
) -> RunHistoryApiService:
    """Build the production SQLite history service."""
    config = RunHistoryConfigLoader().load()
    database = RunHistoryDatabase(
        config=config.storage
    )
    query = RunHistoryQuery(database=database)

    return RunHistoryApiService(reader=query)



def build_default_incident_service(
) -> IncidentApiService:
    """Build the production JSON incident service."""
    config = IncidentManagementConfigLoader().load()
    store = JsonIncidentStore(config=config.storage)

    return IncidentApiService(reader=store)


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



def _incidents_unavailable(
    error: IncidentStorageError,
) -> HTTPException:
    """Convert incident storage failures into HTTP 503."""
    return HTTPException(
        status_code=(
            http_status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        detail="Incident data is temporarily unavailable.",
    )


def create_app(
    history_service: RunHistoryApiService | None = None,
    incident_service: IncidentApiService | None = None,
) -> FastAPI:
    """Create the API with injectable history access."""
    service = (
        history_service
        if history_service is not None
        else build_default_history_service()
    )

    if not isinstance(service, RunHistoryApiService):
        raise TypeError(
            "history_service must be a "
            "RunHistoryApiService."
        )

    incident_api_service = (
        incident_service
        if incident_service is not None
        else build_default_incident_service()
    )

    if not isinstance(
        incident_api_service,
        IncidentApiService,
    ):
        raise TypeError(
            "incident_service must be an "
            "IncidentApiService."
        )

    analytics = DashboardAnalyticsService(
        reader=service.reader
    )

    application = FastAPI(
        title="LabOps AI API",
        description=(
            "Monitoring analytics, diagnostics, "
            "history, and reporting API."
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.mount(
        "/dashboard-assets",
        StaticFiles(
            directory=DASHBOARD_STATIC_DIRECTORY
        ),
        name="dashboard-assets",
    )

    @application.get(
        "/",
        include_in_schema=False,
    )
    def redirect_to_dashboard() -> RedirectResponse:
        """Redirect the root path to the dashboard."""
        return RedirectResponse(
            url="/dashboard",
            status_code=(
                http_status.HTTP_307_TEMPORARY_REDIRECT
            ),
        )

    @application.get(
        "/dashboard",
        include_in_schema=False,
    )
    def get_dashboard() -> FileResponse:
        """Return the interactive monitoring dashboard."""
        return FileResponse(
            DASHBOARD_FILE,
            media_type="text/html",
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
        "/api/v1/dashboard/overview",
        response_model=DashboardOverviewResponse,
        tags=["dashboard"],
    )
    def get_dashboard_overview(
        limit: Annotated[
            int,
            Query(ge=1, le=200),
        ] = 100,
        host_name: Annotated[
            str | None,
            Query(min_length=1, max_length=255),
        ] = None,
    ) -> DashboardOverviewResponse:
        """Return calculated monitoring analytics."""
        normalized_host = _normalize_host_name(
            host_name
        )

        try:
            return analytics.build_overview(
                limit=limit,
                host_name=normalized_host,
            )
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

    @application.get(
        "/api/v1/incidents/summary",
        response_model=IncidentSummaryResponse,
        tags=["incidents"],
    )
    def get_incident_summary(
    ) -> IncidentSummaryResponse:
        """Return incident lifecycle statistics."""
        try:
            return incident_api_service.get_summary()
        except IncidentStorageError as error:
            raise _incidents_unavailable(error) from error

    @application.get(
        "/api/v1/incidents",
        response_model=list[IncidentResponse],
        tags=["incidents"],
    )
    def list_incidents(
        limit: Annotated[
            int,
            Query(ge=1, le=200),
        ] = 50,
        incident_status: Annotated[
            IncidentStatus | None,
            Query(alias="status"),
        ] = None,
        severity: HealthStatus | None = None,
        source_type: IncidentSourceType | None = None,
        active_only: bool | None = None,
    ) -> list[IncidentResponse]:
        """Return filtered infrastructure incidents."""
        try:
            return incident_api_service.list_incidents(
                limit=limit,
                status=incident_status,
                severity=severity,
                source_type=source_type,
                active_only=active_only,
            )
        except IncidentStorageError as error:
            raise _incidents_unavailable(error) from error

    @application.get(
        "/api/v1/incidents/{incident_id}",
        response_model=IncidentResponse,
        tags=["incidents"],
    )
    def get_incident_by_id(
        incident_id: Annotated[
            str,
            ApiPath(min_length=1, max_length=128),
        ],
    ) -> IncidentResponse:
        """Return one incident by identifier."""
        try:
            result = incident_api_service.get_by_id(
                incident_id
            )
        except IncidentStorageError as error:
            raise _incidents_unavailable(error) from error

        if result is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Incident {incident_id} was not found."
                ),
            )

        return result

    @application.get(
        "/api/v1/runs/latest",
        response_model=RunHistoryResponse,
        tags=["runs"],
    )
    def get_latest_run(
        host_name: Annotated[
            str | None,
            Query(min_length=1, max_length=255),
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
                status_code=http_status.HTTP_404_NOT_FOUND,
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
            Query(min_length=1, max_length=255),
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
        "/api/v1/runs/export.csv",
        tags=["reports"],
    )
    def export_runs_csv(
        limit: Annotated[
            int,
            Query(ge=1, le=1000),
        ] = 100,
        health_status: Annotated[
            HealthStatus | None,
            Query(alias="status"),
        ] = None,
        host_name: Annotated[
            str | None,
            Query(min_length=1, max_length=255),
        ] = None,
    ) -> Response:
        """Download filtered run history as CSV."""
        normalized_host = _normalize_host_name(
            host_name
        )

        try:
            entries = service.list_recent(
                limit=limit,
                status=health_status,
                host_name=normalized_host,
            )
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

        report = RunHistoryCsvReportBuilder.build(
            entries
        )
        date_stamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ")

        return Response(
            content=report,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    "attachment; filename="
                    f'"labops-ai-runs-{date_stamp}.csv"'
                )
            },
        )

    @application.get(
        "/api/v1/runs/{run_id}",
        response_model=RunHistoryResponse,
        tags=["runs"],
    )
    def get_run_by_id(
        run_id: Annotated[
            int,
            ApiPath(ge=1),
        ],
    ) -> RunHistoryResponse:
        """Return one monitoring run by identifier."""
        try:
            result = service.get_by_id(run_id)
        except RunHistoryQueryError as error:
            raise _history_unavailable(error) from error

        if result is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Monitoring run {run_id} "
                    "was not found."
                ),
            )

        return result

    return application


app = create_app()
