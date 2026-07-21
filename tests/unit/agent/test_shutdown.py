"""Unit tests for graceful Agent shutdown handling."""
from __future__ import annotations

import signal
from typing import Any
from unittest.mock import patch

import pytest

from labops_ai.agent import (
    ShutdownReason,
    SignalShutdownController,
)
from tests.support.fixture_loader import (
    load_test_fixture,
)


pytestmark = pytest.mark.unit

CASES = load_test_fixture(
    "agent/shutdown_cases.json"
)

ERROR_TYPES: dict[
    str,
    type[Exception],
] = {
    "TypeError": TypeError,
    "ValueError": ValueError,
}


def test_starts_without_shutdown_request() -> None:
    """Start with no stop request or reason."""
    controller = SignalShutdownController()

    assert controller.should_stop() is False
    assert controller.reason is None


@pytest.mark.parametrize(
    "case",
    CASES["signal_cases"],
    ids=lambda case: case["id"],
)
def test_records_requested_shutdown_reason(
    case: dict[str, Any],
) -> None:
    """Store an explicit shutdown request."""
    controller = SignalShutdownController()
    reason = ShutdownReason(
        case["expected_reason"]
    )

    controller.request(reason)

    assert controller.should_stop() is True
    assert controller.reason is reason


def test_preserves_first_shutdown_reason() -> None:
    """Keep the first received shutdown reason."""
    controller = SignalShutdownController()

    controller.request(
        ShutdownReason.INTERRUPT
    )
    controller.request(
        ShutdownReason.TERMINATE
    )

    assert (
        controller.reason
        is ShutdownReason.INTERRUPT
    )


def test_rejects_invalid_shutdown_reason() -> None:
    """Require a supported shutdown reason."""
    controller = SignalShutdownController()

    with pytest.raises(
        TypeError,
        match="reason must be a ShutdownReason",
    ):
        controller.request("SIGTERM")


@pytest.mark.parametrize(
    "case",
    CASES["invalid_wait_values"],
    ids=lambda case: case["id"],
)
def test_rejects_invalid_wait_seconds(
    case: dict[str, Any],
) -> None:
    """Validate interruptible wait duration."""
    controller = SignalShutdownController()
    value = case["value"]

    if (
        isinstance(value, str)
        and value in {"nan", "inf"}
    ):
        value = float(value)

    error_type = ERROR_TYPES[
        case["error_type"]
    ]

    with pytest.raises(
        error_type,
        match=case["match"],
    ):
        controller.wait(value)


def test_installs_and_restores_signal_handlers() -> None:
    """Restore all previous process signal handlers."""
    controller = SignalShutdownController()

    previous_handlers = {
        signal.SIGINT: object(),
        signal.SIGTERM: object(),
    }

    with (
        patch(
            "labops_ai.agent.shutdown.signal.getsignal",
            side_effect=lambda received_signal: (
                previous_handlers[
                    received_signal
                ]
            ),
        ) as getter,
        patch(
            "labops_ai.agent.shutdown.signal.signal",
        ) as setter,
    ):
        with controller:
            assert setter.call_count == 2

        assert setter.call_count == 4

    assert getter.call_count == 2

    restore_calls = (
        setter.call_args_list[-2:]
    )

    assert restore_calls[0].args == (
        signal.SIGINT,
        previous_handlers[signal.SIGINT],
    )
    assert restore_calls[1].args == (
        signal.SIGTERM,
        previous_handlers[signal.SIGTERM],
    )


@pytest.mark.parametrize(
    "case",
    CASES["signal_cases"],
    ids=lambda case: case["id"],
)
def test_maps_os_signal_to_shutdown_reason(
    case: dict[str, Any],
) -> None:
    """Translate installed OS handlers into reasons."""
    controller = SignalShutdownController()
    received_signal = getattr(
        signal,
        case["signal_name"],
    )
    installed_handlers: dict[
        signal.Signals,
        object,
    ] = {}

    def record_handler(
        signal_name,
        handler,
    ):
        installed_handlers[
            signal_name
        ] = handler

    with (
        patch(
            "labops_ai.agent.shutdown.signal.getsignal",
            return_value=signal.SIG_DFL,
        ),
        patch(
            "labops_ai.agent.shutdown.signal.signal",
            side_effect=record_handler,
        ),
    ):
        with controller:
            handler = installed_handlers[
                received_signal
            ]

            assert callable(handler)

            handler(
                received_signal,
                None,
            )

            assert controller.reason is (
                ShutdownReason(
                    case["expected_reason"]
                )
            )
            assert (
                controller.should_stop()
                is True
            )


def test_rejects_nested_signal_installation() -> None:
    """Prevent duplicate handler installation."""
    controller = SignalShutdownController()

    with (
        patch(
            "labops_ai.agent.shutdown.signal.getsignal",
            return_value=signal.SIG_DFL,
        ),
        patch(
            "labops_ai.agent.shutdown.signal.signal",
        ),
    ):
        with controller:
            with pytest.raises(
                RuntimeError,
                match="already installed",
            ):
                controller.__enter__()
