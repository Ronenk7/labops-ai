"""FastAPI routes for the central host registry."""
from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
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


def _registry_unavailable(
    error: HostRegistryError,
) -> HTTPException:
    """Convert registry failures into HTTP 503."""
    return HTTPException(
        status_code=(
            status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        detail=(
            "Host registry is temporarily "
            "unavailable."
        ),
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
            raise _registry_unavailable(error) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return HostResponse.from_snapshot(snapshot)

    @router.get(
        "",
        response_model=list[HostResponse],
    )
    def list_hosts() -> list[HostResponse]:
        """Return all registered hosts with availability."""
        try:
            snapshots = resolved_service.list_all()
        except HostRegistryError as error:
            raise _registry_unavailable(error) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return [
            HostResponse.from_snapshot(snapshot)
            for snapshot in snapshots
        ]

    @router.get(
        "/{host_id}",
        response_model=HostResponse,
    )
    def get_host(
        host_id: Annotated[
            str,
            Path(min_length=1, max_length=128),
        ],
    ) -> HostResponse:
        """Return one registered host by identifier."""
        try:
            snapshot = resolved_service.get_by_id(
                host_id
            )
        except HostRegistryError as error:
            raise _registry_unavailable(error) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {host_id} was not found.",
            )

        return HostResponse.from_snapshot(snapshot)

    return router
