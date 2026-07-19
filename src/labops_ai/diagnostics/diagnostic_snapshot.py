"""Structured snapshot models for complete diagnostic data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

from labops_ai.health_status import HealthStatus
from labops_ai.incidents import IncidentSourceType, IncidentStatus
from labops_ai.logs.log_result import LogFailureReason, LogScanStatus
from labops_ai.network.connectivity_result import (
    ConnectivityCheckStatus,
    ConnectivityCheckType,
    ConnectivityFailureReason,
)
from labops_ai.processes.process_result import (
    ProcessCheckStatus,
    ProcessFailureReason,
)
from labops_ai.services.service_result import (
    ServiceCheckStatus,
    ServiceFailureReason,
)


def _normalize_non_empty_string(field_name: str, value: object) -> str:
    """Validate and normalize a required string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized_value


def _normalize_optional_string(field_name: str, value: object) -> str | None:
    """Validate and normalize an optional populated string."""
    if value is None:
        return None

    return _normalize_non_empty_string(field_name, value)


def _normalize_non_negative_number(field_name: str, value: object) -> float:
    """Validate and normalize a non-negative finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    normalized_value = float(value)

    if not isfinite(normalized_value):
        raise ValueError(f"{field_name} must be finite.")

    if normalized_value < 0.0:
        raise ValueError(f"{field_name} must not be negative.")

    return normalized_value


def _normalize_non_negative_integer(field_name: str, value: object) -> int:
    """Validate a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(f"{field_name} must not be negative.")

    return value


def _normalize_positive_integer(field_name: str, value: object) -> int:
    """Validate a positive integer."""
    normalized_value = _normalize_non_negative_integer(field_name, value)

    if normalized_value == 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return normalized_value


def _normalize_aware_datetime(field_name: str, value: object) -> datetime:
    """Validate and convert a timezone-aware datetime to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must contain timezone information.")

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class DiagnosticSystemMetric:
    """Represent one system metric in a diagnostic snapshot."""

    metric_name: str
    label: str
    value_percent: float
    health_status: HealthStatus

    def __post_init__(self) -> None:
        """Validate and normalize the system metric."""
        metric_name = _normalize_non_empty_string(
            "Diagnostic system metric name", self.metric_name
        )
        label = _normalize_non_empty_string(
            "Diagnostic system metric label", self.label
        )
        value_percent = _normalize_non_negative_number(
            "Diagnostic system metric value", self.value_percent
        )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError("health_status must be a HealthStatus instance.")

        object.__setattr__(self, "metric_name", metric_name)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "value_percent", value_percent)


@dataclass(frozen=True, slots=True)
class DiagnosticNetworkCheck:
    """Represent one DNS or TCP check in a diagnostic snapshot."""

    check_type: ConnectivityCheckType
    target: str
    check_status: ConnectivityCheckStatus
    health_status: HealthStatus
    latency_ms: float | None = None
    resolved_address: str | None = None
    failure_reason: ConnectivityFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the network check."""
        if not isinstance(self.check_type, ConnectivityCheckType):
            raise TypeError(
                "check_type must be a ConnectivityCheckType instance."
            )

        if not isinstance(self.check_status, ConnectivityCheckStatus):
            raise TypeError(
                "check_status must be a ConnectivityCheckStatus instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError("health_status must be a HealthStatus instance.")

        target = _normalize_non_empty_string(
            "Diagnostic network target", self.target
        )
        resolved_address = _normalize_optional_string(
            "Diagnostic resolved address", self.resolved_address
        )
        error_message = _normalize_optional_string(
            "Diagnostic network error message", self.error_message
        )

        latency_ms = None
        if self.latency_ms is not None:
            latency_ms = _normalize_non_negative_number(
                "Diagnostic network latency", self.latency_ms
            )

        if self.failure_reason is not None and not isinstance(
            self.failure_reason, ConnectivityFailureReason
        ):
            raise TypeError(
                "failure_reason must be a ConnectivityFailureReason "
                "instance or None."
            )

        if self.check_status is ConnectivityCheckStatus.PASSED:
            if latency_ms is None:
                raise ValueError(
                    "A passed diagnostic network check must contain latency."
                )

            if self.failure_reason is not None or error_message is not None:
                raise ValueError(
                    "A passed diagnostic network check cannot contain "
                    "failure details."
                )
        else:
            if not isinstance(self.failure_reason, ConnectivityFailureReason):
                raise ValueError(
                    "A failed diagnostic network check must contain "
                    "a failure reason."
                )

        object.__setattr__(self, "target", target)
        object.__setattr__(self, "latency_ms", latency_ms)
        object.__setattr__(self, "resolved_address", resolved_address)
        object.__setattr__(self, "error_message", error_message)


@dataclass(frozen=True, slots=True)
class DiagnosticServiceRecord:
    """Represent one Linux service in a diagnostic snapshot."""

    service_name: str
    label: str
    check_status: ServiceCheckStatus
    health_status: HealthStatus
    load_state: str | None = None
    active_state: str | None = None
    sub_state: str | None = None
    failure_reason: ServiceFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the service snapshot."""
        service_name = _normalize_non_empty_string(
            "Diagnostic service name", self.service_name
        )
        label = _normalize_non_empty_string(
            "Diagnostic service label", self.label
        )

        if not isinstance(self.check_status, ServiceCheckStatus):
            raise TypeError(
                "check_status must be a ServiceCheckStatus instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError("health_status must be a HealthStatus instance.")

        if self.failure_reason is not None and not isinstance(
            self.failure_reason, ServiceFailureReason
        ):
            raise TypeError(
                "failure_reason must be a ServiceFailureReason instance "
                "or None."
            )

        object.__setattr__(self, "service_name", service_name)
        object.__setattr__(self, "label", label)

        for field_name in (
            "load_state",
            "active_state",
            "sub_state",
            "error_message",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_optional_string(
                    field_name.replace("_", " ").title(),
                    getattr(self, field_name),
                ),
            )


@dataclass(frozen=True, slots=True)
class DiagnosticProcessRecord:
    """Represent one monitored process in a diagnostic snapshot."""

    process_name: str
    label: str
    required: bool
    check_status: ProcessCheckStatus
    health_status: HealthStatus
    instance_count: int
    pids: tuple[int, ...]
    total_cpu_percent: float
    total_memory_mb: float
    longest_runtime_seconds: float
    failure_reason: ProcessFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the process snapshot."""
        process_name = _normalize_non_empty_string(
            "Diagnostic process name", self.process_name
        )
        label = _normalize_non_empty_string(
            "Diagnostic process label", self.label
        )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        if not isinstance(self.check_status, ProcessCheckStatus):
            raise TypeError(
                "check_status must be a ProcessCheckStatus instance."
            )

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError("health_status must be a HealthStatus instance.")

        instance_count = _normalize_non_negative_integer(
            "Diagnostic process instance count", self.instance_count
        )

        if not isinstance(self.pids, tuple):
            raise TypeError("Diagnostic process PIDs must be a tuple.")

        for pid in self.pids:
            _normalize_positive_integer("Diagnostic process PID", pid)

        if len(self.pids) != instance_count:
            raise ValueError(
                "Diagnostic process PID count must match instance count."
            )

        total_cpu_percent = _normalize_non_negative_number(
            "Diagnostic process CPU", self.total_cpu_percent
        )
        total_memory_mb = _normalize_non_negative_number(
            "Diagnostic process memory", self.total_memory_mb
        )
        longest_runtime_seconds = _normalize_non_negative_number(
            "Diagnostic process runtime", self.longest_runtime_seconds
        )

        if self.failure_reason is not None and not isinstance(
            self.failure_reason, ProcessFailureReason
        ):
            raise TypeError(
                "failure_reason must be a ProcessFailureReason instance "
                "or None."
            )

        error_message = _normalize_optional_string(
            "Diagnostic process error message", self.error_message
        )

        object.__setattr__(self, "process_name", process_name)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "instance_count", instance_count)
        object.__setattr__(self, "total_cpu_percent", total_cpu_percent)
        object.__setattr__(self, "total_memory_mb", total_memory_mb)
        object.__setattr__(
            self,
            "longest_runtime_seconds",
            longest_runtime_seconds,
        )
        object.__setattr__(self, "error_message", error_message)


@dataclass(frozen=True, slots=True)
class DiagnosticLogRecord:
    """Represent one analyzed log source in a diagnostic snapshot."""

    source_id: str
    label: str
    path: str
    required: bool
    scan_status: LogScanStatus
    health_status: HealthStatus
    total_lines_scanned: int
    match_count: int
    failure_reason: LogFailureReason | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the log snapshot."""
        source_id = _normalize_non_empty_string(
            "Diagnostic log source ID", self.source_id
        )
        label = _normalize_non_empty_string(
            "Diagnostic log label", self.label
        )
        path = _normalize_non_empty_string(
            "Diagnostic log path", self.path
        )

        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean.")

        if not isinstance(self.scan_status, LogScanStatus):
            raise TypeError("scan_status must be a LogScanStatus instance.")

        if not isinstance(self.health_status, HealthStatus):
            raise TypeError("health_status must be a HealthStatus instance.")

        total_lines_scanned = _normalize_non_negative_integer(
            "Diagnostic scanned line count", self.total_lines_scanned
        )
        match_count = _normalize_non_negative_integer(
            "Diagnostic log match count", self.match_count
        )

        if self.failure_reason is not None and not isinstance(
            self.failure_reason, LogFailureReason
        ):
            raise TypeError(
                "failure_reason must be a LogFailureReason instance or None."
            )

        error_message = _normalize_optional_string(
            "Diagnostic log error message", self.error_message
        )

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "path", path)
        object.__setattr__(
            self,
            "total_lines_scanned",
            total_lines_scanned,
        )
        object.__setattr__(self, "match_count", match_count)
        object.__setattr__(self, "error_message", error_message)


@dataclass(frozen=True, slots=True)
class DiagnosticIncidentRecord:
    """Represent one incident in a diagnostic snapshot."""

    incident_id: str
    source_type: IncidentSourceType
    source_id: str
    source_label: str
    severity: HealthStatus
    status: IncidentStatus
    description: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the incident snapshot."""
        incident_id = _normalize_non_empty_string(
            "Diagnostic incident ID", self.incident_id
        )
        source_id = _normalize_non_empty_string(
            "Diagnostic incident source ID", self.source_id
        )
        source_label = _normalize_non_empty_string(
            "Diagnostic incident source label", self.source_label
        )
        description = _normalize_non_empty_string(
            "Diagnostic incident description", self.description
        )

        if not isinstance(self.source_type, IncidentSourceType):
            raise TypeError(
                "source_type must be an IncidentSourceType instance."
            )

        if not isinstance(self.severity, HealthStatus):
            raise TypeError("severity must be a HealthStatus instance.")

        if not isinstance(self.status, IncidentStatus):
            raise TypeError("status must be an IncidentStatus instance.")

        first_seen_at = _normalize_aware_datetime(
            "Diagnostic incident first seen time", self.first_seen_at
        )
        last_seen_at = _normalize_aware_datetime(
            "Diagnostic incident last seen time", self.last_seen_at
        )
        occurrence_count = _normalize_positive_integer(
            "Diagnostic incident occurrence count",
            self.occurrence_count,
        )

        if last_seen_at < first_seen_at:
            raise ValueError(
                "Diagnostic incident last seen time must not be earlier "
                "than first seen time."
            )

        resolved_at = None
        if self.resolved_at is not None:
            resolved_at = _normalize_aware_datetime(
                "Diagnostic incident resolution time",
                self.resolved_at,
            )

        if self.status is IncidentStatus.RESOLVED and resolved_at is None:
            raise ValueError(
                "A resolved diagnostic incident must contain "
                "a resolution time."
            )

        if self.status is not IncidentStatus.RESOLVED and resolved_at is not None:
            raise ValueError(
                "An active diagnostic incident cannot contain "
                "a resolution time."
            )

        object.__setattr__(self, "incident_id", incident_id)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_label", source_label)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "first_seen_at", first_seen_at)
        object.__setattr__(self, "last_seen_at", last_seen_at)
        object.__setattr__(self, "occurrence_count", occurrence_count)
        object.__setattr__(self, "resolved_at", resolved_at)


@dataclass(frozen=True, slots=True)
class DiagnosticSnapshot:
    """Represent all monitoring and incident data from one run."""

    generated_at: datetime
    host_name: str
    system_metrics: tuple[DiagnosticSystemMetric, ...]
    system_overall_status: HealthStatus
    network_checks: tuple[DiagnosticNetworkCheck, ...]
    network_overall_status: HealthStatus
    services: tuple[DiagnosticServiceRecord, ...]
    service_overall_status: HealthStatus
    processes: tuple[DiagnosticProcessRecord, ...]
    process_overall_status: HealthStatus
    logs: tuple[DiagnosticLogRecord, ...]
    log_overall_status: HealthStatus
    incidents: tuple[DiagnosticIncidentRecord, ...]

    def __post_init__(self) -> None:
        """Validate the complete diagnostic snapshot."""
        generated_at = _normalize_aware_datetime(
            "Diagnostic snapshot generation time",
            self.generated_at,
        )
        host_name = _normalize_non_empty_string(
            "Diagnostic snapshot host name",
            self.host_name,
        )

        self._validate_collection(
            "system_metrics",
            self.system_metrics,
            DiagnosticSystemMetric,
            allow_empty=False,
        )
        self._validate_collection(
            "network_checks",
            self.network_checks,
            DiagnosticNetworkCheck,
            allow_empty=False,
        )
        self._validate_collection(
            "services",
            self.services,
            DiagnosticServiceRecord,
            allow_empty=False,
        )
        self._validate_collection(
            "processes",
            self.processes,
            DiagnosticProcessRecord,
            allow_empty=False,
        )
        self._validate_collection(
            "logs",
            self.logs,
            DiagnosticLogRecord,
            allow_empty=False,
        )
        self._validate_collection(
            "incidents",
            self.incidents,
            DiagnosticIncidentRecord,
            allow_empty=True,
        )

        for field_name in (
            "system_overall_status",
            "network_overall_status",
            "service_overall_status",
            "process_overall_status",
            "log_overall_status",
        ):
            if not isinstance(getattr(self, field_name), HealthStatus):
                raise TypeError(
                    f"{field_name} must be a HealthStatus instance."
                )

        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "host_name", host_name)

    @property
    def active_incident_count(self) -> int:
        """Return the number of active incidents."""
        return sum(
            incident.status is not IncidentStatus.RESOLVED
            for incident in self.incidents
        )

    @property
    def resolved_incident_count(self) -> int:
        """Return the number of resolved incidents."""
        return sum(
            incident.status is IncidentStatus.RESOLVED
            for incident in self.incidents
        )

    @property
    def overall_status(self) -> HealthStatus:
        """Return the highest current monitoring severity."""
        statuses = {
            self.system_overall_status,
            self.network_overall_status,
            self.service_overall_status,
            self.process_overall_status,
            self.log_overall_status,
        }

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL

        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    @staticmethod
    def _validate_collection(
        field_name: str,
        value: object,
        expected_type: type,
        *,
        allow_empty: bool,
    ) -> None:
        """Validate one tuple collection in the snapshot."""
        if not isinstance(value, tuple):
            raise TypeError(f"{field_name} must be a tuple.")

        if not allow_empty and not value:
            raise ValueError(f"{field_name} must not be empty.")

        for item in value:
            if not isinstance(item, expected_type):
                raise TypeError(
                    f"Every item in {field_name} must be a "
                    f"{expected_type.__name__} instance."
                )