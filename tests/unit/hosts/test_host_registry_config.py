"""Tests for host-registry configuration."""
from __future__ import annotations

import json

import pytest

from labops_ai.hosts.registry_loader import (
    HostRegistryConfigLoader,
)


pytestmark = pytest.mark.unit


def write_config(tmp_path, configuration):
    """Write one temporary registry configuration."""
    path = tmp_path / "host_registry.json"
    path.write_text(
        json.dumps(configuration),
        encoding="utf-8",
    )
    return path


def valid_configuration():
    """Return one valid registry configuration."""
    return {
        "storage": {
            "database_path": "runtime/hosts/hosts.sqlite3",
            "busy_timeout_seconds": 5.0,
        },
        "availability": {
            "stale_after_seconds": 30,
            "offline_after_seconds": 120,
        },
    }


def test_loads_default_configuration() -> None:
    """Load the production host-registry settings."""
    config = HostRegistryConfigLoader().load()

    assert (
        config.storage.database_path
        == "runtime/hosts/host_registry.sqlite3"
    )
    assert config.storage.busy_timeout_seconds == 5.0
    assert config.availability.stale_after_seconds == 30
    assert config.availability.offline_after_seconds == 120


def test_rejects_missing_section(tmp_path) -> None:
    """Reject a configuration without availability."""
    configuration = valid_configuration()
    del configuration["availability"]

    path = write_config(tmp_path, configuration)

    with pytest.raises(
        ValueError,
        match="Missing required keys",
    ):
        HostRegistryConfigLoader(path).load()


def test_rejects_unknown_storage_key(tmp_path) -> None:
    """Reject unsupported storage settings."""
    configuration = valid_configuration()
    configuration["storage"]["unexpected"] = True

    path = write_config(tmp_path, configuration)

    with pytest.raises(
        ValueError,
        match="Unsupported keys",
    ):
        HostRegistryConfigLoader(path).load()


def test_rejects_invalid_availability_order(
    tmp_path,
) -> None:
    """Require offline threshold after stale threshold."""
    configuration = valid_configuration()
    configuration["availability"] = {
        "stale_after_seconds": 120,
        "offline_after_seconds": 30,
    }

    path = write_config(tmp_path, configuration)

    with pytest.raises(
        ValueError,
        match="must be greater",
    ):
        HostRegistryConfigLoader(path).load()


def test_rejects_invalid_database_suffix(
    tmp_path,
) -> None:
    """Require a supported SQLite filename."""
    configuration = valid_configuration()
    configuration["storage"][
        "database_path"
    ] = "runtime/hosts/registry.txt"

    path = write_config(tmp_path, configuration)

    with pytest.raises(
        ValueError,
        match="suffixes",
    ):
        HostRegistryConfigLoader(path).load()
