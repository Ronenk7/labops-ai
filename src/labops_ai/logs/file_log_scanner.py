"""Read text log files and identify configured matching rules."""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.logs.log_config import (
    LogAnalyzerConfig,
    LogSourceConfig,
)
from labops_ai.logs.log_result import (
    LogFailureReason,
    LogLine,
    LogMatch,
    LogScanStatus,
    LogSourceResult,
)


LogLineReader = Callable[
    [Path, str, int],
    tuple[LogLine, ...],
]


def read_log_tail(
    path: Path,
    encoding: str,
    max_lines: int,
) -> tuple[LogLine, ...]:
    """Read up to the final configured number of log lines."""
    lines: deque[LogLine] = deque(maxlen=max_lines)

    with path.open("r", encoding=encoding) as log_file:
        for line_number, raw_line in enumerate(
            log_file,
            start=1,
        ):
            lines.append(
                LogLine(
                    line_number=line_number,
                    text=raw_line.rstrip("\r\n"),
                )
            )

    return tuple(lines)


@dataclass(frozen=True, slots=True)
class FileLogScanner:
    """Scan configured text log files for matching rules."""

    config: LogAnalyzerConfig
    reader: LogLineReader = read_log_tail

    def __post_init__(self) -> None:
        """Validate configuration and reader dependency."""
        if not isinstance(self.config, LogAnalyzerConfig):
            raise TypeError(
                "config must be a LogAnalyzerConfig instance."
            )

        if not callable(self.reader):
            raise TypeError("reader must be callable.")

    def scan(
        self,
        source: LogSourceConfig,
    ) -> LogSourceResult:
        """Read and analyze one configured log source."""
        if not isinstance(source, LogSourceConfig):
            raise TypeError(
                "source must be a LogSourceConfig instance."
            )

        resolved_path = self._resolve_path(source.path)

        try:
            lines = self.reader(
                resolved_path,
                self.config.collection.encoding,
                self.config.collection.max_lines_per_source,
            )
        except FileNotFoundError as error:
            return self._build_error_result(
                source=source,
                reason=LogFailureReason.FILE_NOT_FOUND,
                error=error,
                fallback_message="Log file was not found.",
            )
        except PermissionError as error:
            return self._build_error_result(
                source=source,
                reason=LogFailureReason.ACCESS_DENIED,
                error=error,
                fallback_message="Access to the log file was denied.",
            )
        except UnicodeDecodeError as error:
            return self._build_error_result(
                source=source,
                reason=LogFailureReason.DECODE_ERROR,
                error=error,
                fallback_message="Log file could not be decoded.",
            )
        except OSError as error:
            return self._build_error_result(
                source=source,
                reason=LogFailureReason.READ_ERROR,
                error=error,
                fallback_message="Log file could not be read.",
            )
        except Exception as error:
            return self._build_error_result(
                source=source,
                reason=LogFailureReason.UNKNOWN_ERROR,
                error=error,
                fallback_message=(
                    "An unexpected log scanning error occurred."
                ),
            )

        self._validate_reader_result(lines)

        matches = self._find_matches(lines)

        return LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=source.required,
            status=LogScanStatus.ANALYZED,
            total_lines_scanned=len(lines),
            matches=matches,
        )

    @staticmethod
    def _resolve_path(configured_path: str) -> Path:
        """Resolve an absolute or project-relative log path."""
        path = Path(configured_path).expanduser()

        if path.is_absolute():
            return path

        return PROJECT_ROOT / path

    @staticmethod
    def _validate_reader_result(
        lines: object,
    ) -> None:
        """Validate the result returned by the line reader."""
        if not isinstance(lines, tuple):
            raise TypeError(
                "Log line reader must return a tuple."
            )

        for line in lines:
            if not isinstance(line, LogLine):
                raise TypeError(
                    "Log line reader must return LogLine instances."
                )

    def _find_matches(
        self,
        lines: tuple[LogLine, ...],
    ) -> tuple[LogMatch, ...]:
        """Match every configured rule against every log line."""
        matches: list[LogMatch] = []

        for line in lines:
            for rule in self.config.rules:
                flags = (
                    0
                    if rule.case_sensitive
                    else re.IGNORECASE
                )

                if re.search(rule.pattern, line.text, flags):
                    matches.append(
                        LogMatch(
                            rule_id=rule.rule_id,
                            rule_label=rule.label,
                            severity=rule.severity,
                            line_number=line.line_number,
                            content=line.text,
                        )
                    )

        return tuple(matches)

    @staticmethod
    def _build_error_result(
        source: LogSourceConfig,
        reason: LogFailureReason,
        error: Exception,
        fallback_message: str,
    ) -> LogSourceResult:
        """Build a normalized log scanning error."""
        error_message = str(error).strip() or fallback_message

        return LogSourceResult(
            source_id=source.source_id,
            label=source.label,
            path=source.path,
            required=source.required,
            status=LogScanStatus.CHECK_ERROR,
            total_lines_scanned=0,
            failure_reason=reason,
            error_message=error_message,
        )