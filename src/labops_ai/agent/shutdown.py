"""Graceful operating-system signal handling."""
from __future__ import annotations

import signal
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from threading import Event
from types import FrameType
from typing import Self


class ShutdownReason(str, Enum):
    """Describe why the Agent was asked to stop."""

    INTERRUPT = "INTERRUPT"
    TERMINATE = "TERMINATE"


@dataclass(slots=True)
class SignalShutdownController:
    """Convert SIGINT and SIGTERM into a stop predicate."""

    _event: Event = field(
        default_factory=Event,
        init=False,
        repr=False,
    )
    _reason: ShutdownReason | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _previous_handlers: dict[
        signal.Signals,
        object,
    ] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _installed: bool = field(
        default=False,
        init=False,
        repr=False,
    )

    @property
    def reason(self) -> ShutdownReason | None:
        """Return the first received shutdown reason."""
        return self._reason

    def should_stop(self) -> bool:
        """Return whether shutdown was requested."""
        return self._event.is_set()

    def request(
        self,
        reason: ShutdownReason,
    ) -> None:
        """Request graceful shutdown."""
        if not isinstance(
            reason,
            ShutdownReason,
        ):
            raise TypeError(
                "reason must be a ShutdownReason."
            )

        if self._reason is None:
            self._reason = reason
            self._event.set()

    def wait(
        self,
        seconds: float,
    ) -> None:
        """Wait until timeout or shutdown request."""
        if (
            isinstance(seconds, bool)
            or not isinstance(
                seconds,
                (int, float),
            )
        ):
            raise TypeError(
                "seconds must be numeric."
            )

        normalized_seconds = float(seconds)

        if (
            not isfinite(normalized_seconds)
            or normalized_seconds < 0
        ):
            raise ValueError(
                "seconds must be finite and "
                "non-negative."
            )

        self._event.wait(normalized_seconds)

    def __enter__(self) -> Self:
        """Install graceful shutdown signal handlers."""
        if self._installed:
            raise RuntimeError(
                "Signal handlers are already installed."
            )

        installed_signals: list[
            signal.Signals
        ] = []

        try:
            for received_signal in (
                signal.SIGINT,
                signal.SIGTERM,
            ):
                self._previous_handlers[
                    received_signal
                ] = signal.getsignal(
                    received_signal
                )

                signal.signal(
                    received_signal,
                    self._handle_signal,
                )
                installed_signals.append(
                    received_signal
                )
        except BaseException:
            for received_signal in reversed(
                installed_signals
            ):
                signal.signal(
                    received_signal,
                    self._previous_handlers[
                        received_signal
                    ],
                )

            self._previous_handlers.clear()
            raise

        self._installed = True
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        traceback,
    ) -> None:
        """Restore the previous signal handlers."""
        if not self._installed:
            return

        for received_signal in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            signal.signal(
                received_signal,
                self._previous_handlers[
                    received_signal
                ],
            )

        self._previous_handlers.clear()
        self._installed = False

    def _handle_signal(
        self,
        signal_number: int,
        frame: FrameType | None,
    ) -> None:
        """Translate one operating-system signal."""
        received_signal = signal.Signals(
            signal_number
        )

        reason_by_signal = {
            signal.SIGINT: (
                ShutdownReason.INTERRUPT
            ),
            signal.SIGTERM: (
                ShutdownReason.TERMINATE
            ),
        }

        self.request(
            reason_by_signal[received_signal]
        )
