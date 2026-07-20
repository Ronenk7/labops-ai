"""Local Linux metadata providers for the host agent."""
from __future__ import annotations

import platform
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass


TextReader = Callable[[], str]
OsReleaseReader = Callable[
    [],
    Mapping[str, str],
]


def _normalize_text(
    value: object,
    field_name: str,
) -> str:
    """Validate and normalize required metadata."""
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return normalized


def resolve_primary_address() -> str:
    """Return the primary IPv4 address of this host."""
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        ) as connection:
            connection.connect(
                ("192.0.2.1", 9)
            )

            return _normalize_text(
                connection.getsockname()[0],
                "address",
            )

    except (
        OSError,
        ValueError,
    ):
        try:
            return _normalize_text(
                socket.gethostbyname(
                    socket.gethostname()
                ),
                "address",
            )

        except (
            OSError,
            ValueError,
        ) as error:
            raise RuntimeError(
                "Unable to determine the local "
                "host address."
            ) from error


@dataclass(frozen=True, slots=True)
class LocalHostProviders:
    """Provide metadata from the local Linux host."""

    host_name_reader: TextReader = (
        socket.gethostname
    )
    address_reader: TextReader = (
        resolve_primary_address
    )
    os_release_reader: OsReleaseReader = (
        platform.freedesktop_os_release
    )
    platform_reader: TextReader = (
        platform.platform
    )
    architecture_reader: TextReader = (
        platform.machine
    )

    def __post_init__(self) -> None:
        """Validate all provider dependencies."""
        readers = (
            (
                "host_name_reader",
                self.host_name_reader,
            ),
            (
                "address_reader",
                self.address_reader,
            ),
            (
                "os_release_reader",
                self.os_release_reader,
            ),
            (
                "platform_reader",
                self.platform_reader,
            ),
            (
                "architecture_reader",
                self.architecture_reader,
            ),
        )

        for reader_name, reader in readers:
            if not callable(reader):
                raise TypeError(
                    f"{reader_name} must be callable."
                )

    def host_name(self) -> str:
        """Return the local host name."""
        return _normalize_text(
            self.host_name_reader(),
            "host_name",
        )

    def address(self) -> str:
        """Return the local primary IPv4 address."""
        return _normalize_text(
            self.address_reader(),
            "address",
        )

    def operating_system(self) -> str:
        """Return a readable operating-system name."""
        try:
            release_info = (
                self.os_release_reader()
            )
        except OSError:
            release_info = {}

        if not isinstance(
            release_info,
            Mapping,
        ):
            raise TypeError(
                "os_release_reader must return "
                "a mapping."
            )

        pretty_name = release_info.get(
            "PRETTY_NAME"
        )

        if (
            isinstance(pretty_name, str)
            and pretty_name.strip()
        ):
            return pretty_name.strip()

        description_parts: list[str] = []

        for key in (
            "NAME",
            "VERSION_ID",
        ):
            value = release_info.get(key)

            if (
                isinstance(value, str)
                and value.strip()
            ):
                description_parts.append(
                    value.strip()
                )

        if description_parts:
            return " ".join(
                description_parts
            )

        return _normalize_text(
            self.platform_reader(),
            "operating_system",
        )

    def architecture(self) -> str:
        """Return the local machine architecture."""
        return _normalize_text(
            self.architecture_reader(),
            "architecture",
        )