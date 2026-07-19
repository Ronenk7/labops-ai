"""FastAPI routes for real-time infrastructure metrics."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from labops_ai.api.live_metrics import LiveMetricsCollector


def build_live_router(
    collector: LiveMetricsCollector | None = None,
) -> APIRouter:
    """Build isolated live metric API routes."""
    resolved_collector = (
        collector
        if collector is not None
        else LiveMetricsCollector()
    )

    if not isinstance(
        resolved_collector,
        LiveMetricsCollector,
    ):
        raise TypeError(
            "collector must be a LiveMetricsCollector."
        )

    router = APIRouter(
        prefix="/api/v1/live",
        tags=["live"],
    )

    @router.get("/snapshot")
    def get_live_snapshot() -> dict[str, object]:
        """Return one immediate infrastructure sample."""
        return resolved_collector.collect()

    @router.get("/stream")
    async def stream_live_metrics() -> StreamingResponse:
        """Stream infrastructure samples using SSE."""
        return StreamingResponse(
            resolved_collector.stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return router
