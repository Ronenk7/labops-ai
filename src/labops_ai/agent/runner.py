"""Compose and run the production host agent."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from importlib.metadata import (
    PackageNotFoundError,
    version,
)
from typing import Protocol

from labops_ai.agent.agent import (
    Clock,
    HeartbeatSender,
    HostAgent,
    MonitoringExecutor,
    MonitoringRunSender,
    Sleeper,
)
from labops_ai.agent.config import (
    HostAgentConfig,
)
from labops_ai.agent.http_sender import (
    HttpHeartbeatSender,
)
from labops_ai.agent.run_sender import (
    HttpMonitoringRunSender,
)
from labops_ai.agent.loader import (
    HostAgentConfigLoader,
)
from labops_ai.agent.providers import (
    LocalHostProviders,
)
from labops_ai.hosts import HostHeartbeat
from labops_ai.monitoring import (
    run_remote_monitoring_snapshot,
)


_DISTRIBUTION_NAME = "labops-ai"
_DEVELOPMENT_VERSION = "0.1.0-dev"


class AgentConfigLoaderProtocol(Protocol):
    """Define configuration loading for the runtime."""

    def load(self) -> HostAgentConfig:
        """Load validated host-agent configuration."""
        ...


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def resolve_agent_version() -> str:
    """Return the installed LabOps AI package version."""
    try:
        resolved_version = version(
            _DISTRIBUTION_NAME
        )
    except PackageNotFoundError:
        resolved_version = _DEVELOPMENT_VERSION

    normalized = resolved_version.strip()

    if not normalized:
        raise RuntimeError(
            "The LabOps AI package version "
            "must not be empty."
        )

    return normalized


def build_default_agent(
    *,
    config_loader: (
        AgentConfigLoaderProtocol | None
    ) = None,
    providers: LocalHostProviders | None = None,
    sender: HeartbeatSender | None = None,
    monitoring_sender: MonitoringRunSender | None = None,
    monitoring_executor: MonitoringExecutor | None = None,
    clock: Clock = utc_now,
    sleeper: Sleeper = time.sleep,
    agent_version: str | None = None,
) -> HostAgent:
    """Build the production host-agent composition."""
    resolved_loader = (
        config_loader
        if config_loader is not None
        else HostAgentConfigLoader()
    )

    load_method = getattr(
        resolved_loader,
        "load",
        None,
    )

    if not callable(load_method):
        raise TypeError(
            "config_loader must provide a callable "
            "load method."
        )

    config = load_method()

    if not isinstance(
        config,
        HostAgentConfig,
    ):
        raise TypeError(
            "config_loader.load must return a "
            "HostAgentConfig."
        )

    resolved_providers = (
        providers
        if providers is not None
        else LocalHostProviders()
    )

    if not isinstance(
        resolved_providers,
        LocalHostProviders,
    ):
        raise TypeError(
            "providers must be a "
            "LocalHostProviders instance."
        )

    resolved_sender = (
        sender
        if sender is not None
        else HttpHeartbeatSender()
    )

    resolved_monitoring_sender = (
        monitoring_sender
        if monitoring_sender is not None
        else HttpMonitoringRunSender()
    )
    resolved_monitoring_executor = (
        monitoring_executor
        if monitoring_executor is not None
        else run_remote_monitoring_snapshot
    )

    resolved_version = (
        resolve_agent_version()
        if agent_version is None
        else agent_version
    )

    return HostAgent(
        config=config,
        sender=resolved_sender,
        clock=clock,
        host_name_provider=(
            resolved_providers.host_name
        ),
        address_provider=(
            resolved_providers.address
        ),
        operating_system_provider=(
            resolved_providers.operating_system
        ),
        architecture_provider=(
            resolved_providers.architecture
        ),
        agent_version=resolved_version,
        sleeper=sleeper,
        monitoring_executor=(
            resolved_monitoring_executor
        ),
        monitoring_sender=(
            resolved_monitoring_sender
        ),
    )


def run_agent_once(
    agent: HostAgent | None = None,
) -> HostHeartbeat:
    """Run one production heartbeat cycle."""
    resolved_agent = (
        agent
        if agent is not None
        else build_default_agent()
    )

    if not isinstance(
        resolved_agent,
        HostAgent,
    ):
        raise TypeError(
            "agent must be a HostAgent."
        )

    return resolved_agent.run_once()