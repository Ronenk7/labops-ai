"""Run the LabOps AI API using validated configuration."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import uvicorn

from labops_ai.api.server_config import (
    ApiServerConfig,
    ApiServerConfigLoader,
)


def run_api_server(
    config: ApiServerConfig | None = None,
    *,
    runner: Callable[..., Any] = uvicorn.run,
) -> None:
    """Start Uvicorn with validated production settings."""
    if not callable(runner):
        raise TypeError("runner must be callable.")

    resolved_config = (
        config
        if config is not None
        else ApiServerConfigLoader().load()
    )

    if not isinstance(
        resolved_config,
        ApiServerConfig,
    ):
        raise TypeError(
            "config must be an ApiServerConfig."
        )

    runner(
        "labops_ai.api:app",
        host=resolved_config.host,
        port=resolved_config.port,
        log_level=resolved_config.log_level,
        access_log=resolved_config.access_log,
        proxy_headers=resolved_config.proxy_headers,
        workers=resolved_config.workers,
    )


def main() -> None:
    """Run the configured LabOps AI API server."""
    run_api_server()


if __name__ == "__main__":
    main()
