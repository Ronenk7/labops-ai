"""Collect Linux process metrics using psutil."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import time
from typing import Any

import psutil

from labops_ai.processes.process_config import (
    ProcessCollectionConfig,
    ProcessTargetConfig,
)
from labops_ai.processes.process_result import (
    ProcessCheckResult,
    ProcessCheckStatus,
    ProcessFailureReason,
    ProcessInstanceSnapshot,
)


ProcessIterator = Callable[[], Iterable[Any]]
Clock = Callable[[], float]


def iterate_processes() -> Iterable[psutil.Process]:
    """Return an iterator over current operating-system processes."""
    return psutil.process_iter()


@dataclass(frozen=True, slots=True)
class PsutilProcessChecker:
    """Find configured processes and collect their metrics."""

    collection_config: ProcessCollectionConfig
    process_iterator: ProcessIterator = iterate_processes
    clock: Clock = time

    def __post_init__(self) -> None:
        """Validate configuration and injected dependencies."""
        if not isinstance(
            self.collection_config,
            ProcessCollectionConfig,
        ):
            raise TypeError(
                "collection_config must be a "
                "ProcessCollectionConfig instance."
            )

        if not callable(self.process_iterator):
            raise TypeError(
                "process_iterator must be callable."
            )

        if not callable(self.clock):
            raise TypeError("clock must be callable.")

    def check(
        self,
        target: ProcessTargetConfig,
    ) -> ProcessCheckResult:
        """Find all matching processes and collect their metrics."""
        if not isinstance(target, ProcessTargetConfig):
            raise TypeError(
                "target must be a ProcessTargetConfig instance."
            )

        snapshots: list[ProcessInstanceSnapshot] = []
        access_errors: list[str] = []

        try:
            for process in self.process_iterator():
                try:
                    process_name = process.name()
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    continue

                if (
                    process_name.casefold()
                    != target.process_name.casefold()
                ):
                    continue

                try:
                    snapshots.append(
                        self._collect_snapshot(process)
                    )
                except psutil.AccessDenied as error:
                    access_errors.append(
                        str(error).strip()
                        or "Access denied while reading process."
                    )
                except (
                    psutil.NoSuchProcess,
                    psutil.ZombieProcess,
                ):
                    continue
        except (psutil.Error, OSError) as error:
            return self._build_error_result(
                target=target,
                reason=ProcessFailureReason.PROCESS_SCAN_FAILED,
                error=error,
                fallback_message="Process scan failed.",
            )
        except Exception as error:
            return self._build_error_result(
                target=target,
                reason=ProcessFailureReason.UNKNOWN_ERROR,
                error=error,
                fallback_message=(
                    "An unexpected process scan error occurred."
                ),
            )

        if snapshots:
            return ProcessCheckResult(
                process_name=target.process_name,
                label=target.label,
                required=target.required,
                status=ProcessCheckStatus.RUNNING,
                instances=tuple(snapshots),
            )

        if access_errors:
            return ProcessCheckResult(
                process_name=target.process_name,
                label=target.label,
                required=target.required,
                status=ProcessCheckStatus.CHECK_ERROR,
                failure_reason=(
                    ProcessFailureReason.ACCESS_DENIED
                ),
                error_message="; ".join(access_errors),
            )

        return ProcessCheckResult(
            process_name=target.process_name,
            label=target.label,
            required=target.required,
            status=ProcessCheckStatus.NOT_RUNNING,
        )

    def _collect_snapshot(
        self,
        process: Any,
    ) -> ProcessInstanceSnapshot:
        """Collect one process instance snapshot."""
        cpu_percent = process.cpu_percent(
            interval=self.collection_config.cpu_sample_interval_seconds
        )
        memory_bytes = process.memory_info().rss
        runtime_seconds = max(
            0.0,
            self.clock() - process.create_time(),
        )

        return ProcessInstanceSnapshot(
            pid=int(process.pid),
            cpu_percent=cpu_percent,
            memory_mb=memory_bytes / (1024.0 * 1024.0),
            runtime_seconds=runtime_seconds,
        )

    @staticmethod
    def _build_error_result(
        target: ProcessTargetConfig,
        reason: ProcessFailureReason,
        error: Exception,
        fallback_message: str,
    ) -> ProcessCheckResult:
        """Build a normalized process check error."""
        error_message = str(error).strip() or fallback_message

        return ProcessCheckResult(
            process_name=target.process_name,
            label=target.label,
            required=target.required,
            status=ProcessCheckStatus.CHECK_ERROR,
            failure_reason=reason,
            error_message=error_message,
        )