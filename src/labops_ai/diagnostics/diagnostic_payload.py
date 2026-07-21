"""Parse validated remote diagnostic JSON payloads."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from labops_ai.diagnostics.diagnostic_snapshot import (
    DiagnosticIncidentRecord,
    DiagnosticLogRecord,
    DiagnosticNetworkCheck,
    DiagnosticProcessRecord,
    DiagnosticServiceRecord,
    DiagnosticSnapshot,
    DiagnosticSystemMetric,
)
from labops_ai.health_status import HealthStatus
from labops_ai.incidents import (
    IncidentSourceType,
    IncidentStatus,
)
from labops_ai.logs.log_result import (
    LogFailureReason,
    LogScanStatus,
)
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


_DIAGNOSTIC_SCHEMA_VERSION = 1

EnumValue = TypeVar(
    "EnumValue",
    bound=Enum,
)


class DiagnosticPayloadError(ValueError):
    """Represent invalid remote diagnostic data."""


def _mapping(
    value: object,
    field_name: str,
) -> Mapping[str, Any]:
    """Require one JSON object."""
    if not isinstance(value, Mapping):
        raise DiagnosticPayloadError(
            f"{field_name} must be an object."
        )

    return value


def _list(
    value: object,
    field_name: str,
) -> list[Any]:
    """Require one JSON array."""
    if not isinstance(value, list):
        raise DiagnosticPayloadError(
            f"{field_name} must be an array."
        )

    return value


def _required(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> Any:
    """Read one required JSON field."""
    if key not in payload:
        raise DiagnosticPayloadError(
            f"{field_name} is required."
        )

    return payload[key]


def _required_string(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> str:
    """Read one populated string."""
    value = _required(
        payload,
        key,
        field_name,
    )

    if not isinstance(value, str):
        raise DiagnosticPayloadError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise DiagnosticPayloadError(
            f"{field_name} must not be empty."
        )

    return normalized


def _optional_string(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> str | None:
    """Read one optional populated string."""
    value = payload.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise DiagnosticPayloadError(
            f"{field_name} must be a string or null."
        )

    normalized = value.strip()

    if not normalized:
        raise DiagnosticPayloadError(
            f"{field_name} must not be empty."
        )

    return normalized


def _required_boolean(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> bool:
    """Read one required boolean."""
    value = _required(
        payload,
        key,
        field_name,
    )

    if not isinstance(value, bool):
        raise DiagnosticPayloadError(
            f"{field_name} must be a boolean."
        )

    return value


def _required_integer(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> int:
    """Read one required integer."""
    value = _required(
        payload,
        key,
        field_name,
    )

    if isinstance(value, bool) or not isinstance(value, int):
        raise DiagnosticPayloadError(
            f"{field_name} must be an integer."
        )

    return value


def _required_number(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> float:
    """Read one required numeric value."""
    value = _required(
        payload,
        key,
        field_name,
    )

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise DiagnosticPayloadError(
            f"{field_name} must be numeric."
        )

    return float(value)


def _optional_number(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> float | None:
    """Read one optional numeric value."""
    value = payload.get(key)

    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise DiagnosticPayloadError(
            f"{field_name} must be numeric or null."
        )

    return float(value)


def _datetime_value(
    value: object,
    field_name: str,
) -> datetime:
    """Parse one timezone-aware ISO-8601 timestamp."""
    if not isinstance(value, str):
        raise DiagnosticPayloadError(
            f"{field_name} must be an ISO-8601 string."
        )

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise DiagnosticPayloadError(
            f"{field_name} is not valid ISO-8601."
        ) from error

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise DiagnosticPayloadError(
            f"{field_name} must include timezone information."
        )

    return parsed


def _required_datetime(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> datetime:
    """Read one required timestamp."""
    return _datetime_value(
        _required(
            payload,
            key,
            field_name,
        ),
        field_name,
    )


def _optional_datetime(
    payload: Mapping[str, Any],
    key: str,
    field_name: str,
) -> datetime | None:
    """Read one optional timestamp."""
    value = payload.get(key)

    if value is None:
        return None

    return _datetime_value(
        value,
        field_name,
    )


def _enum_value(
    enum_type: type[EnumValue],
    value: object,
    field_name: str,
) -> EnumValue:
    """Parse one supported enumeration value."""
    if not isinstance(value, str):
        raise DiagnosticPayloadError(
            f"{field_name} must be a string."
        )

    try:
        return enum_type(value)
    except ValueError as error:
        raise DiagnosticPayloadError(
            f"{field_name} contains an unsupported value."
        ) from error


def _required_enum(
    payload: Mapping[str, Any],
    key: str,
    enum_type: type[EnumValue],
    field_name: str,
) -> EnumValue:
    """Read one required enumeration."""
    return _enum_value(
        enum_type,
        _required(
            payload,
            key,
            field_name,
        ),
        field_name,
    )


def _optional_enum(
    payload: Mapping[str, Any],
    key: str,
    enum_type: type[EnumValue],
    field_name: str,
) -> EnumValue | None:
    """Read one optional enumeration."""
    value = payload.get(key)

    if value is None:
        return None

    return _enum_value(
        enum_type,
        value,
        field_name,
    )


def _parse_system_metrics(
    section: Mapping[str, Any],
) -> tuple[DiagnosticSystemMetric, ...]:
    """Build system metric domain records."""
    records = _list(
        _required(
            section,
            "metrics",
            "system.metrics",
        ),
        "system.metrics",
    )

    return tuple(
        DiagnosticSystemMetric(
            metric_name=_required_string(
                record,
                "metric_name",
                f"system.metrics[{index}].metric_name",
            ),
            label=_required_string(
                record,
                "label",
                f"system.metrics[{index}].label",
            ),
            value_percent=_required_number(
                record,
                "value_percent",
                (
                    f"system.metrics[{index}]"
                    ".value_percent"
                ),
            ),
            health_status=_required_enum(
                record,
                "health_status",
                HealthStatus,
                (
                    f"system.metrics[{index}]"
                    ".health_status"
                ),
            ),
        )
        for index, raw_record in enumerate(records)
        for record in (
            _mapping(
                raw_record,
                f"system.metrics[{index}]",
            ),
        )
    )


def _parse_network_checks(
    section: Mapping[str, Any],
) -> tuple[DiagnosticNetworkCheck, ...]:
    """Build network check domain records."""
    records = _list(
        _required(
            section,
            "checks",
            "network.checks",
        ),
        "network.checks",
    )

    return tuple(
        DiagnosticNetworkCheck(
            check_type=_required_enum(
                record,
                "check_type",
                ConnectivityCheckType,
                (
                    f"network.checks[{index}]"
                    ".check_type"
                ),
            ),
            target=_required_string(
                record,
                "target",
                f"network.checks[{index}].target",
            ),
            check_status=_required_enum(
                record,
                "check_status",
                ConnectivityCheckStatus,
                (
                    f"network.checks[{index}]"
                    ".check_status"
                ),
            ),
            health_status=_required_enum(
                record,
                "health_status",
                HealthStatus,
                (
                    f"network.checks[{index}]"
                    ".health_status"
                ),
            ),
            latency_ms=_optional_number(
                record,
                "latency_ms",
                (
                    f"network.checks[{index}]"
                    ".latency_ms"
                ),
            ),
            resolved_address=_optional_string(
                record,
                "resolved_address",
                (
                    f"network.checks[{index}]"
                    ".resolved_address"
                ),
            ),
            failure_reason=_optional_enum(
                record,
                "failure_reason",
                ConnectivityFailureReason,
                (
                    f"network.checks[{index}]"
                    ".failure_reason"
                ),
            ),
            error_message=_optional_string(
                record,
                "error_message",
                (
                    f"network.checks[{index}]"
                    ".error_message"
                ),
            ),
        )
        for index, raw_record in enumerate(records)
        for record in (
            _mapping(
                raw_record,
                f"network.checks[{index}]",
            ),
        )
    )


def _parse_services(
    section: Mapping[str, Any],
) -> tuple[DiagnosticServiceRecord, ...]:
    """Build service check domain records."""
    records = _list(
        _required(
            section,
            "records",
            "services.records",
        ),
        "services.records",
    )

    return tuple(
        DiagnosticServiceRecord(
            service_name=_required_string(
                record,
                "service_name",
                (
                    f"services.records[{index}]"
                    ".service_name"
                ),
            ),
            label=_required_string(
                record,
                "label",
                f"services.records[{index}].label",
            ),
            check_status=_required_enum(
                record,
                "check_status",
                ServiceCheckStatus,
                (
                    f"services.records[{index}]"
                    ".check_status"
                ),
            ),
            health_status=_required_enum(
                record,
                "health_status",
                HealthStatus,
                (
                    f"services.records[{index}]"
                    ".health_status"
                ),
            ),
            load_state=_optional_string(
                record,
                "load_state",
                (
                    f"services.records[{index}]"
                    ".load_state"
                ),
            ),
            active_state=_optional_string(
                record,
                "active_state",
                (
                    f"services.records[{index}]"
                    ".active_state"
                ),
            ),
            sub_state=_optional_string(
                record,
                "sub_state",
                (
                    f"services.records[{index}]"
                    ".sub_state"
                ),
            ),
            failure_reason=_optional_enum(
                record,
                "failure_reason",
                ServiceFailureReason,
                (
                    f"services.records[{index}]"
                    ".failure_reason"
                ),
            ),
            error_message=_optional_string(
                record,
                "error_message",
                (
                    f"services.records[{index}]"
                    ".error_message"
                ),
            ),
        )
        for index, raw_record in enumerate(records)
        for record in (
            _mapping(
                raw_record,
                f"services.records[{index}]",
            ),
        )
    )


def _parse_processes(
    section: Mapping[str, Any],
) -> tuple[DiagnosticProcessRecord, ...]:
    """Build process check domain records."""
    records = _list(
        _required(
            section,
            "records",
            "processes.records",
        ),
        "processes.records",
    )

    parsed: list[DiagnosticProcessRecord] = []

    for index, raw_record in enumerate(records):
        record = _mapping(
            raw_record,
            f"processes.records[{index}]",
        )
        raw_pids = _list(
            _required(
                record,
                "pids",
                f"processes.records[{index}].pids",
            ),
            f"processes.records[{index}].pids",
        )

        pids: list[int] = []

        for pid_index, pid in enumerate(raw_pids):
            if isinstance(pid, bool) or not isinstance(pid, int):
                raise DiagnosticPayloadError(
                    "processes.records"
                    f"[{index}].pids[{pid_index}] "
                    "must be an integer."
                )

            pids.append(pid)

        parsed.append(
            DiagnosticProcessRecord(
                process_name=_required_string(
                    record,
                    "process_name",
                    (
                        f"processes.records[{index}]"
                        ".process_name"
                    ),
                ),
                label=_required_string(
                    record,
                    "label",
                    (
                        f"processes.records[{index}]"
                        ".label"
                    ),
                ),
                required=_required_boolean(
                    record,
                    "required",
                    (
                        f"processes.records[{index}]"
                        ".required"
                    ),
                ),
                check_status=_required_enum(
                    record,
                    "check_status",
                    ProcessCheckStatus,
                    (
                        f"processes.records[{index}]"
                        ".check_status"
                    ),
                ),
                health_status=_required_enum(
                    record,
                    "health_status",
                    HealthStatus,
                    (
                        f"processes.records[{index}]"
                        ".health_status"
                    ),
                ),
                instance_count=_required_integer(
                    record,
                    "instance_count",
                    (
                        f"processes.records[{index}]"
                        ".instance_count"
                    ),
                ),
                pids=tuple(pids),
                total_cpu_percent=_required_number(
                    record,
                    "total_cpu_percent",
                    (
                        f"processes.records[{index}]"
                        ".total_cpu_percent"
                    ),
                ),
                total_memory_mb=_required_number(
                    record,
                    "total_memory_mb",
                    (
                        f"processes.records[{index}]"
                        ".total_memory_mb"
                    ),
                ),
                longest_runtime_seconds=(
                    _required_number(
                        record,
                        "longest_runtime_seconds",
                        (
                            f"processes.records[{index}]"
                            ".longest_runtime_seconds"
                        ),
                    )
                ),
                failure_reason=_optional_enum(
                    record,
                    "failure_reason",
                    ProcessFailureReason,
                    (
                        f"processes.records[{index}]"
                        ".failure_reason"
                    ),
                ),
                error_message=_optional_string(
                    record,
                    "error_message",
                    (
                        f"processes.records[{index}]"
                        ".error_message"
                    ),
                ),
            )
        )

    return tuple(parsed)


def _parse_logs(
    section: Mapping[str, Any],
) -> tuple[DiagnosticLogRecord, ...]:
    """Build log analysis domain records."""
    records = _list(
        _required(
            section,
            "records",
            "logs.records",
        ),
        "logs.records",
    )

    return tuple(
        DiagnosticLogRecord(
            source_id=_required_string(
                record,
                "source_id",
                f"logs.records[{index}].source_id",
            ),
            label=_required_string(
                record,
                "label",
                f"logs.records[{index}].label",
            ),
            path=_required_string(
                record,
                "path",
                f"logs.records[{index}].path",
            ),
            required=_required_boolean(
                record,
                "required",
                f"logs.records[{index}].required",
            ),
            scan_status=_required_enum(
                record,
                "scan_status",
                LogScanStatus,
                f"logs.records[{index}].scan_status",
            ),
            health_status=_required_enum(
                record,
                "health_status",
                HealthStatus,
                (
                    f"logs.records[{index}]"
                    ".health_status"
                ),
            ),
            total_lines_scanned=_required_integer(
                record,
                "total_lines_scanned",
                (
                    f"logs.records[{index}]"
                    ".total_lines_scanned"
                ),
            ),
            match_count=_required_integer(
                record,
                "match_count",
                f"logs.records[{index}].match_count",
            ),
            failure_reason=_optional_enum(
                record,
                "failure_reason",
                LogFailureReason,
                (
                    f"logs.records[{index}]"
                    ".failure_reason"
                ),
            ),
            error_message=_optional_string(
                record,
                "error_message",
                (
                    f"logs.records[{index}]"
                    ".error_message"
                ),
            ),
        )
        for index, raw_record in enumerate(records)
        for record in (
            _mapping(
                raw_record,
                f"logs.records[{index}]",
            ),
        )
    )


def _parse_incidents(
    section: Mapping[str, Any],
) -> tuple[DiagnosticIncidentRecord, ...]:
    """Build incident domain records."""
    records = _list(
        _required(
            section,
            "records",
            "incidents.records",
        ),
        "incidents.records",
    )

    return tuple(
        DiagnosticIncidentRecord(
            incident_id=_required_string(
                record,
                "incident_id",
                (
                    f"incidents.records[{index}]"
                    ".incident_id"
                ),
            ),
            source_type=_required_enum(
                record,
                "source_type",
                IncidentSourceType,
                (
                    f"incidents.records[{index}]"
                    ".source_type"
                ),
            ),
            source_id=_required_string(
                record,
                "source_id",
                (
                    f"incidents.records[{index}]"
                    ".source_id"
                ),
            ),
            source_label=_required_string(
                record,
                "source_label",
                (
                    f"incidents.records[{index}]"
                    ".source_label"
                ),
            ),
            severity=_required_enum(
                record,
                "severity",
                HealthStatus,
                (
                    f"incidents.records[{index}]"
                    ".severity"
                ),
            ),
            status=_required_enum(
                record,
                "status",
                IncidentStatus,
                (
                    f"incidents.records[{index}]"
                    ".status"
                ),
            ),
            description=_required_string(
                record,
                "description",
                (
                    f"incidents.records[{index}]"
                    ".description"
                ),
            ),
            first_seen_at=_required_datetime(
                record,
                "first_seen_at",
                (
                    f"incidents.records[{index}]"
                    ".first_seen_at"
                ),
            ),
            last_seen_at=_required_datetime(
                record,
                "last_seen_at",
                (
                    f"incidents.records[{index}]"
                    ".last_seen_at"
                ),
            ),
            occurrence_count=_required_integer(
                record,
                "occurrence_count",
                (
                    f"incidents.records[{index}]"
                    ".occurrence_count"
                ),
            ),
            resolved_at=_optional_datetime(
                record,
                "resolved_at",
                (
                    f"incidents.records[{index}]"
                    ".resolved_at"
                ),
            ),
        )
        for index, raw_record in enumerate(records)
        for record in (
            _mapping(
                raw_record,
                f"incidents.records[{index}]",
            ),
        )
    )


def _validate_status_consistency(
    payload: Mapping[str, Any],
    summary: Mapping[str, Any],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Require summary values to match parsed details."""
    expected = {
        "system_status": (
            snapshot.system_overall_status
        ),
        "network_status": (
            snapshot.network_overall_status
        ),
        "service_status": (
            snapshot.service_overall_status
        ),
        "process_status": (
            snapshot.process_overall_status
        ),
        "log_status": snapshot.log_overall_status,
    }

    for field_name, actual_status in expected.items():
        reported = _required_enum(
            summary,
            field_name,
            HealthStatus,
            f"summary.{field_name}",
        )

        if reported != actual_status:
            raise DiagnosticPayloadError(
                f"summary.{field_name} does not "
                "match its diagnostic section."
            )

    reported_overall = _required_enum(
        payload,
        "overall_status",
        HealthStatus,
        "overall_status",
    )

    if reported_overall != snapshot.overall_status:
        raise DiagnosticPayloadError(
            "overall_status does not match "
            "the diagnostic sections."
        )


def _validate_incident_counts(
    section: Mapping[str, Any],
    snapshot: DiagnosticSnapshot,
) -> None:
    """Require incident counters to match records."""
    active_count = _required_integer(
        section,
        "active_count",
        "incidents.active_count",
    )
    resolved_count = _required_integer(
        section,
        "resolved_count",
        "incidents.resolved_count",
    )

    if active_count != snapshot.active_incident_count:
        raise DiagnosticPayloadError(
            "incidents.active_count does not "
            "match incident records."
        )

    if resolved_count != snapshot.resolved_incident_count:
        raise DiagnosticPayloadError(
            "incidents.resolved_count does not "
            "match incident records."
        )


def parse_diagnostic_payload(
    payload: Mapping[str, Any],
) -> DiagnosticSnapshot:
    """Convert one remote JSON report into domain models."""
    root = _mapping(
        payload,
        "diagnostics",
    )

    schema_version = _required(
        root,
        "schema_version",
        "schema_version",
    )

    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != _DIAGNOSTIC_SCHEMA_VERSION
    ):
        raise DiagnosticPayloadError(
            "schema_version is unsupported."
        )

    summary = _mapping(
        _required(
            root,
            "summary",
            "summary",
        ),
        "summary",
    )
    system = _mapping(
        _required(
            root,
            "system",
            "system",
        ),
        "system",
    )
    network = _mapping(
        _required(
            root,
            "network",
            "network",
        ),
        "network",
    )
    services = _mapping(
        _required(
            root,
            "services",
            "services",
        ),
        "services",
    )
    processes = _mapping(
        _required(
            root,
            "processes",
            "processes",
        ),
        "processes",
    )
    logs = _mapping(
        _required(
            root,
            "logs",
            "logs",
        ),
        "logs",
    )
    incidents = _mapping(
        _required(
            root,
            "incidents",
            "incidents",
        ),
        "incidents",
    )

    try:
        snapshot = DiagnosticSnapshot(
            generated_at=_required_datetime(
                root,
                "generated_at",
                "generated_at",
            ),
            host_name=_required_string(
                root,
                "host_name",
                "host_name",
            ),
            system_metrics=_parse_system_metrics(
                system
            ),
            system_overall_status=_required_enum(
                system,
                "overall_status",
                HealthStatus,
                "system.overall_status",
            ),
            network_checks=_parse_network_checks(
                network
            ),
            network_overall_status=_required_enum(
                network,
                "overall_status",
                HealthStatus,
                "network.overall_status",
            ),
            services=_parse_services(services),
            service_overall_status=_required_enum(
                services,
                "overall_status",
                HealthStatus,
                "services.overall_status",
            ),
            processes=_parse_processes(processes),
            process_overall_status=_required_enum(
                processes,
                "overall_status",
                HealthStatus,
                "processes.overall_status",
            ),
            logs=_parse_logs(logs),
            log_overall_status=_required_enum(
                logs,
                "overall_status",
                HealthStatus,
                "logs.overall_status",
            ),
            incidents=_parse_incidents(incidents),
        )
    except DiagnosticPayloadError:
        raise
    except (TypeError, ValueError) as error:
        raise DiagnosticPayloadError(
            f"Diagnostic domain validation failed: {error}"
        ) from error

    _validate_status_consistency(
        root,
        summary,
        snapshot,
    )
    _validate_incident_counts(
        incidents,
        snapshot,
    )

    if _required_integer(
        summary,
        "active_incidents",
        "summary.active_incidents",
    ) != snapshot.active_incident_count:
        raise DiagnosticPayloadError(
            "summary.active_incidents does not "
            "match incident records."
        )

    if _required_integer(
        summary,
        "resolved_incidents",
        "summary.resolved_incidents",
    ) != snapshot.resolved_incident_count:
        raise DiagnosticPayloadError(
            "summary.resolved_incidents does not "
            "match incident records."
        )

    return snapshot
