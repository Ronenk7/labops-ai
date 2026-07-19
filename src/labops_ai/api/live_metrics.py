"""Collect and stream lightweight live Linux metrics."""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, AsyncIterator

import psutil


_MIN_INTERVAL_SECONDS = 1.0
_MAX_INTERVAL_SECONDS = 60.0


def _round_metric(value: float) -> float:
    """Round one live metric consistently."""
    return round(max(0.0, float(value)), 2)


def _calculate_status(
    cpu_percent: float,
    memory_percent: float,
    disk_percent: float,
) -> str:
    """Calculate the current live pressure status."""
    highest_value = max(
        cpu_percent,
        memory_percent,
        disk_percent,
    )

    if highest_value >= 90.0:
        return "CRITICAL"

    if highest_value >= 75.0:
        return "WARNING"

    return "HEALTHY"


@dataclass(slots=True)
class LiveMetricsCollector:
    """Collect safe lightweight metrics for the live dashboard."""

    sample_interval_seconds: float = 2.0
    disk_path: str = "/"
    _lock: Lock = field(
        default_factory=Lock,
        init=False,
        repr=False,
    )
    _last_net: Any = field(
        init=False,
        repr=False,
    )
    _last_sampled_at: float = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Validate configuration and initialize rate counters."""
        if isinstance(
            self.sample_interval_seconds,
            bool,
        ) or not isinstance(
            self.sample_interval_seconds,
            (int, float),
        ):
            raise TypeError(
                "sample_interval_seconds must be numeric."
            )

        interval = float(self.sample_interval_seconds)

        if not (
            _MIN_INTERVAL_SECONDS
            <= interval
            <= _MAX_INTERVAL_SECONDS
        ):
            raise ValueError(
                "sample_interval_seconds must be "
                "between 1 and 60."
            )

        if not isinstance(self.disk_path, str):
            raise TypeError("disk_path must be a string.")

        disk_path = self.disk_path.strip()

        if not disk_path:
            raise ValueError(
                "disk_path must not be empty."
            )

        self.sample_interval_seconds = interval
        self.disk_path = disk_path
        self._last_net = psutil.net_io_counters()
        self._last_sampled_at = time.monotonic()

        psutil.cpu_percent(interval=None)

    def collect(self) -> dict[str, object]:
        """Collect one current live metric sample."""
        sampled_at = time.monotonic()

        with self._lock:
            network = psutil.net_io_counters()
            elapsed = max(
                sampled_at - self._last_sampled_at,
                0.001,
            )

            receive_bps = (
                network.bytes_recv
                - self._last_net.bytes_recv
            ) / elapsed
            transmit_bps = (
                network.bytes_sent
                - self._last_net.bytes_sent
            ) / elapsed

            self._last_net = network
            self._last_sampled_at = sampled_at

        cpu_percent = _round_metric(
            psutil.cpu_percent(interval=None)
        )
        memory_percent = _round_metric(
            psutil.virtual_memory().percent
        )
        disk_percent = _round_metric(
            psutil.disk_usage(self.disk_path).percent
        )

        try:
            load_1, load_5, load_15 = os.getloadavg()
        except (AttributeError, OSError):
            load_1 = load_5 = load_15 = 0.0

        uptime_seconds = max(
            0.0,
            time.time() - psutil.boot_time(),
        )

        return {
            "sampled_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": _calculate_status(
                cpu_percent,
                memory_percent,
                disk_percent,
            ),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "network_receive_bps": _round_metric(
                receive_bps
            ),
            "network_transmit_bps": _round_metric(
                transmit_bps
            ),
            "load_1": _round_metric(load_1),
            "load_5": _round_metric(load_5),
            "load_15": _round_metric(load_15),
            "uptime_seconds": _round_metric(
                uptime_seconds
            ),
            "process_count": len(psutil.pids()),
            "cpu_count": int(
                psutil.cpu_count() or 1
            ),
        }

    async def stream(self) -> AsyncIterator[str]:
        """Yield Server-Sent Events continuously."""
        while True:
            payload = self.collect()

            yield (
                "event: metrics\n"
                "data: "
                + json.dumps(
                    payload,
                    separators=(",", ":"),
                )
                + "\n\n"
            )

            await asyncio.sleep(
                self.sample_interval_seconds
            )
