"""FastAPI routes for the central host registry."""
from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from labops_ai.api.host_schemas import (
    HostHeartbeatRequest,
    HostResponse,
)
from labops_ai.hosts import (
    HostRegistryConfigLoader,
    HostRegistryError,
    HostRegistryService,
    HostStatusEvaluator,
    SqliteHostRegistry,
)


def build_default_host_service() -> HostRegistryService:
    """Build the production host-registry service."""
    config = HostRegistryConfigLoader().load()

    registry = SqliteHostRegistry(
        database_path=config.storage.database_path,
        busy_timeout_seconds=(
            config.storage.busy_timeout_seconds
        ),
    )
    evaluator = HostStatusEvaluator(
        policy=config.availability
    )

    return HostRegistryService(
        registry=registry,
        evaluator=evaluator,
    )


def build_host_router(
    service: HostRegistryService | None = None,
) -> APIRouter:
    """Build host-registry API routes."""
    resolved_service = (
        service
        if service is not None
        else build_default_host_service()
    )

    if not isinstance(
        resolved_service,
        HostRegistryService,
    ):
        raise TypeError(
            "service must be a HostRegistryService."
        )

    router = APIRouter(
        prefix="/api/v1/hosts",
        tags=["hosts"],
    )

    @router.post(
        "/heartbeat",
        response_model=HostResponse,
        status_code=status.HTTP_200_OK,
    )
    def record_heartbeat(
        request: HostHeartbeatRequest,
    ) -> HostResponse:
        """Create or update a host from its heartbeat."""
        try:
            snapshot = resolved_service.record_heartbeat(
                request.to_domain()
            )
        except HostRegistryError as error:
            raise HTTPException(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ),
                detail=(
                    "Host registry is temporarily "
                    "unavailable."
                ),
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return HostResponse.from_snapshot(snapshot)

    return router
