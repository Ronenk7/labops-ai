"""Tests for local host metadata providers."""
from __future__ import annotations

import pytest

from labops_ai.agent import (
    LocalHostProviders,
)


pytestmark = pytest.mark.unit


def test_reads_and_normalizes_local_metadata() -> None:
    """Return normalized metadata from readers."""
    providers = LocalHostProviders(
        host_name_reader=(
            lambda: " lab-node-01 "
        ),
        address_reader=(
            lambda: " 10.0.0.10 "
        ),
        os_release_reader=lambda: {
            "PRETTY_NAME": (
                " Ubuntu 24.04 LTS "
            ),
        },
        platform_reader=lambda: "unused",
        architecture_reader=(
            lambda: " x86_64 "
        ),
    )

    assert providers.host_name() == (
        "lab-node-01"
    )
    assert providers.address() == (
        "10.0.0.10"
    )
    assert providers.operating_system() == (
        "Ubuntu 24.04 LTS"
    )
    assert providers.architecture() == (
        "x86_64"
    )


def test_builds_os_name_without_pretty_name() -> None:
    """Combine distribution name and version."""
    providers = LocalHostProviders(
        os_release_reader=lambda: {
            "NAME": "Ubuntu",
            "VERSION_ID": "24.04",
        },
    )

    assert providers.operating_system() == (
        "Ubuntu 24.04"
    )


def test_falls_back_to_platform_description() -> None:
    """Use platform data when os-release is missing."""
    def unavailable_os_release():
        raise OSError(
            "os-release is unavailable"
        )

    providers = LocalHostProviders(
        os_release_reader=(
            unavailable_os_release
        ),
        platform_reader=lambda: (
            "Linux-6.8.0-x86_64"
        ),
    )

    assert providers.operating_system() == (
        "Linux-6.8.0-x86_64"
    )


def test_rejects_empty_host_name() -> None:
    """Reject missing local host metadata."""
    providers = LocalHostProviders(
        host_name_reader=lambda: "   ",
    )

    with pytest.raises(
        ValueError,
        match="host_name must not be empty",
    ):
        providers.host_name()


def test_rejects_invalid_os_release_result() -> None:
    """Require os-release data to be a mapping."""
    providers = LocalHostProviders(
        os_release_reader=lambda: (
            "Ubuntu 24.04"
        ),
    )

    with pytest.raises(
        TypeError,
        match="must return a mapping",
    ):
        providers.operating_system()


def test_rejects_non_callable_reader() -> None:
    """Require injectable readers to be callable."""
    with pytest.raises(
        TypeError,
        match="address_reader must be callable",
    ):
        LocalHostProviders(
            address_reader="10.0.0.10",
        )