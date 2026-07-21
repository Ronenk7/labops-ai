"""Unit tests for local host metadata providers."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from labops_ai.agent import (
    LocalHostProviders,
    resolve_primary_address,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/provider_cases.json"
)

ERROR_TYPES: dict[
    str,
    type[Exception],
] = {
    "TypeError": TypeError,
    "ValueError": ValueError,
}


def test_reads_and_normalizes_local_metadata() -> None:
    """Return normalized values from every reader."""
    case = CASES["normalized_metadata"]
    values = case["input"]

    providers = LocalHostProviders(
        host_name_reader=(
            lambda: values["host_name"]
        ),
        address_reader=(
            lambda: values["address"]
        ),
        os_release_reader=lambda: {
            "PRETTY_NAME": values["pretty_name"],
        },
        platform_reader=(
            lambda: values["platform"]
        ),
        architecture_reader=(
            lambda: values["architecture"]
        ),
    )

    expected = case["expected"]

    assert providers.host_name() == (
        expected["host_name"]
    )
    assert providers.address() == (
        expected["address"]
    )
    assert providers.operating_system() == (
        expected["operating_system"]
    )
    assert providers.architecture() == (
        expected["architecture"]
    )


@pytest.mark.parametrize(
    "case",
    CASES["operating_system_cases"],
    ids=lambda case: case["id"],
)
def test_builds_operating_system_description(
    case: dict[str, Any],
) -> None:
    """Resolve the best available OS description."""
    def read_os_release():
        if (
            case["release_behavior"]
            == "raise_os_error"
        ):
            raise OSError(
                "os-release is unavailable"
            )

        return case["release_info"]

    providers = LocalHostProviders(
        os_release_reader=read_os_release,
        platform_reader=(
            lambda: case["platform"]
        ),
    )

    assert providers.operating_system() == (
        case["expected"]
    )


@pytest.mark.parametrize(
    "case",
    CASES["invalid_metadata_cases"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_metadata(
    case: dict[str, Any],
) -> None:
    """Reject empty and incorrectly typed metadata."""
    reader_name = case["reader_name"]
    value = case["value"]

    keyword_arguments: dict[
        str,
        object,
    ] = {
        reader_name: lambda: value,
    }

    if (
        case["method_name"]
        == "operating_system"
    ):
        keyword_arguments[
            "os_release_reader"
        ] = lambda: {}

    providers = LocalHostProviders(
        **keyword_arguments
    )
    method = getattr(
        providers,
        case["method_name"],
    )
    error_type = ERROR_TYPES[
        case["error_type"]
    ]

    with pytest.raises(
        error_type,
        match=case["match"],
    ):
        method()


@pytest.mark.parametrize(
    "case",
    CASES["invalid_os_release_results"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_os_release_result(
    case: dict[str, Any],
) -> None:
    """Require os-release readers to return mappings."""
    providers = LocalHostProviders(
        os_release_reader=(
            lambda: case["value"]
        ),
    )

    with pytest.raises(
        TypeError,
        match="must return a mapping",
    ):
        providers.operating_system()


@pytest.mark.parametrize(
    "case",
    CASES["non_callable_readers"],
    ids=lambda case: case["id"],
)
def test_rejects_non_callable_reader(
    case: dict[str, Any],
) -> None:
    """Require every operating-system reader to be callable."""
    with pytest.raises(
        TypeError,
        match=(
            f'{case["reader_name"]} '
            "must be callable"
        ),
    ):
        LocalHostProviders(
            **{
                case["reader_name"]:
                case["value"]
            }
        )


def test_resolves_primary_address_through_udp_route() -> None:
    """Use the local address selected for a UDP route."""
    case = CASES["primary_address"][
        "udp_success"
    ]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.getsockname.return_value = (
        case["socket_address"],
        54321,
    )

    with patch(
        "labops_ai.agent.providers.socket.socket",
        return_value=connection,
    ) as socket_factory:
        result = resolve_primary_address()

    assert result == case["expected"]

    socket_factory.assert_called_once()
    connection.connect.assert_called_once_with(
        tuple(
            CASES["primary_address"][
                "probe_target"
            ]
        )
    )
    connection.getsockname.assert_called_once_with()


def test_falls_back_to_hostname_resolution() -> None:
    """Use DNS when UDP route detection fails."""
    case = CASES["primary_address"][
        "dns_fallback"
    ]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.connect.side_effect = OSError(
        "No network route"
    )

    with (
        patch(
            "labops_ai.agent.providers.socket.socket",
            return_value=connection,
        ),
        patch(
            "labops_ai.agent.providers.socket.gethostname",
            return_value=case["host_name"],
        ) as hostname_reader,
        patch(
            "labops_ai.agent.providers.socket.gethostbyname",
            return_value=case[
                "resolved_address"
            ],
        ) as resolver,
    ):
        result = resolve_primary_address()

    assert result == case["expected"]

    hostname_reader.assert_called_once_with()
    resolver.assert_called_once_with(
        case["host_name"]
    )


def test_raises_when_address_cannot_be_resolved() -> None:
    """Report failure when both resolution methods fail."""
    case = CASES["primary_address"][
        "total_failure"
    ]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.connect.side_effect = OSError(
        "No network route"
    )

    with (
        patch(
            "labops_ai.agent.providers.socket.socket",
            return_value=connection,
        ),
        patch(
            "labops_ai.agent.providers.socket.gethostname",
            return_value=case["host_name"],
        ),
        patch(
            "labops_ai.agent.providers.socket.gethostbyname",
            side_effect=OSError(
                case["dns_error"]
            ),
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match=case["expected_message"],
        ):
            resolve_primary_address()
