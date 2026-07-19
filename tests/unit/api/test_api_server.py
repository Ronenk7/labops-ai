"""Tests for the configured production API server."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from labops_ai.api.server import run_api_server
from labops_ai.api.server_config import (
    ApiServerConfig,
    ApiServerConfigLoader,
)
from tests.support.fixture_loader import load_test_fixture


pytestmark = pytest.mark.unit
CASES = load_test_fixture(
    "config/api_server_cases.json"
)


def write_config(
    tmp_path: Path,
    payload: object,
) -> Path:
    """Write one temporary API configuration."""
    path = tmp_path / "api_server.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path


def test_loads_default_configuration() -> None:
    config = ApiServerConfigLoader().load()

    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.workers == 1


def test_loads_custom_configuration(
    tmp_path: Path,
) -> None:
    config = ApiServerConfigLoader(
        write_config(tmp_path, CASES["valid"])
    ).load()

    assert config.port == 8100
    assert config.log_level == "warning"
    assert config.proxy_headers is True


def test_rejects_invalid_port(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError):
        ApiServerConfigLoader(
            write_config(
                tmp_path,
                CASES["invalid_port"],
            )
        ).load()


@pytest.mark.parametrize(
    ("field_name", "value", "error"),
    [
        ("host", "", ValueError),
        ("port", "8000", TypeError),
        ("log_level", "verbose", ValueError),
        ("access_log", 1, TypeError),
        ("workers", 0, ValueError),
    ],
)
def test_rejects_invalid_settings(
    field_name: str,
    value: object,
    error: type[Exception],
) -> None:
    values = dict(CASES["valid"])
    values[field_name] = value

    with pytest.raises(error):
        ApiServerConfig(**values)


def test_passes_configuration_to_uvicorn() -> None:
    calls: list[tuple[object, dict[str, object]]] = []

    def runner(
        application: object,
        **kwargs: object,
    ) -> None:
        calls.append((application, kwargs))

    config = ApiServerConfig(**CASES["valid"])

    run_api_server(config, runner=runner)

    application, arguments = calls[0]

    assert application == "labops_ai.api:app"
    assert arguments["host"] == "127.0.0.1"
    assert arguments["port"] == 8100
    assert arguments["workers"] == 2


def test_systemd_manager_has_valid_shell_syntax() -> None:
    subprocess.run(
        [
            "bash",
            "-n",
            "scripts/manage_api_systemd_user.sh",
        ],
        check=True,
    )
