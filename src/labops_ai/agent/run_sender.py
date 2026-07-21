"""HTTP delivery for complete remote monitoring runs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from labops_ai.agent.agent import (
    MonitoringRunDeliveryError,
)
from labops_ai.diagnostics import (
    DiagnosticSnapshot,
    build_diagnostic_payload,
)


HttpOpener = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class HttpMonitoringRunSender:
    """Send complete diagnostic runs to the central API."""

    opener: HttpOpener = urlopen

    def __post_init__(self) -> None:
        """Validate the HTTP dependency."""
        if not callable(self.opener):
            raise TypeError(
                "opener must be callable."
            )

    def send(
        self,
        *,
        url: str,
        snapshot: DiagnosticSnapshot,
        timeout_seconds: float,
    ) -> None:
        """Send one diagnostic snapshot as JSON."""
        if not isinstance(url, str):
            raise TypeError(
                "url must be a string."
            )

        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError(
                "url must not be empty."
            )

        if not isinstance(
            snapshot,
            DiagnosticSnapshot,
        ):
            raise TypeError(
                "snapshot must be a "
                "DiagnosticSnapshot."
            )

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(
                timeout_seconds,
                (int, float),
            )
        ):
            raise TypeError(
                "timeout_seconds must be numeric."
            )

        normalized_timeout = float(
            timeout_seconds
        )

        if (
            not isfinite(normalized_timeout)
            or normalized_timeout <= 0
        ):
            raise ValueError(
                "timeout_seconds must be "
                "finite and positive."
            )

        payload = {
            "diagnostics": build_diagnostic_payload(
                snapshot
            )
        }

        request = Request(
            url=normalized_url,
            data=json.dumps(
                payload,
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with self.opener(
                request,
                timeout=normalized_timeout,
            ) as response:
                status_code = getattr(
                    response,
                    "status",
                    200,
                )
        except HTTPError as error:
            raise MonitoringRunDeliveryError(
                "Failed to deliver monitoring run: "
                f"server returned HTTP {error.code}."
            ) from error
        except (
            URLError,
            TimeoutError,
            OSError,
        ) as error:
            raise MonitoringRunDeliveryError(
                "Failed to deliver monitoring run "
                f"to {normalized_url}."
            ) from error

        if not 200 <= status_code < 300:
            raise MonitoringRunDeliveryError(
                "Failed to deliver monitoring run: "
                f"server returned HTTP {status_code}."
            )
