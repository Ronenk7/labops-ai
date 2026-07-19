"""Tests for lightweight live metric collection."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labops_ai.api import live_metrics
from labops_ai.api.live_metrics import (
    LiveMetricsCollector,
)


pytestmark = pytest.mark.unit


def test_collects_deterministic_live_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network_samples = iter(
        (
            SimpleNamespace(
                bytes_recv=1000,
                bytes_sent=500,
            ),
            SimpleNamespace(
                bytes_recv=5000,
                bytes_sent=2500,
            ),
        )
    )
    monotonic_samples = iter((100.0, 102.0))

    monkeypatch.setattr(
        live_metrics.psutil,
        "net_io_counters",
        lambda: next(network_samples),
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "cpu_percent",
        lambda interval=None: 24.5,
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=41.2),
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "disk_usage",
        lambda path: SimpleNamespace(percent=31.7),
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "boot_time",
        lambda: live_metrics.time.time() - 3600,
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "pids",
        lambda: [1, 2, 3],
    )
    monkeypatch.setattr(
        live_metrics.psutil,
        "cpu_count",
        lambda: 8,
    )
    monkeypatch.setattr(
        live_metrics.time,
        "monotonic",
        lambda: next(monotonic_samples),
    )
    monkeypatch.setattr(
        live_metrics.os,
        "getloadavg",
        lambda: (0.4, 0.3, 0.2),
    )

    collector = LiveMetricsCollector(
        sample_interval_seconds=2.0
    )
    result = collector.collect()

    assert result["status"] == "HEALTHY"
    assert result["cpu_percent"] == 24.5
    assert result["memory_percent"] == 41.2
    assert result["disk_percent"] == 31.7
    assert result["network_receive_bps"] == 2000.0
    assert result["network_transmit_bps"] == 1000.0
    assert result["process_count"] == 3
    assert result["cpu_count"] == 8


@pytest.mark.parametrize(
    "interval",
    (0, 0.5, 61),
)
def test_rejects_invalid_stream_interval(
    interval: float,
) -> None:
    with pytest.raises(ValueError):
        LiveMetricsCollector(
            sample_interval_seconds=interval
        )
