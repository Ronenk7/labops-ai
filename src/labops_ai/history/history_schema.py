"""SQLite schema used for persistent monitoring run history."""


RUN_HISTORY_SCHEMA_VERSION = 1


RUN_HISTORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS history_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS monitoring_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    host_name TEXT NOT NULL,

    overall_status TEXT NOT NULL
        CHECK (
            overall_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    system_status TEXT NOT NULL
        CHECK (
            system_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    network_status TEXT NOT NULL
        CHECK (
            network_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    service_status TEXT NOT NULL
        CHECK (
            service_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    process_status TEXT NOT NULL
        CHECK (
            process_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    log_status TEXT NOT NULL
        CHECK (
            log_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    active_incident_count INTEGER NOT NULL
        CHECK (active_incident_count >= 0),

    resolved_incident_count INTEGER NOT NULL
        CHECK (resolved_incident_count >= 0),

    bundle_id TEXT NOT NULL UNIQUE,
    archive_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_metrics (
    run_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    label TEXT NOT NULL,
    value_percent REAL NOT NULL
        CHECK (value_percent >= 0),
    health_status TEXT NOT NULL
        CHECK (
            health_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),

    PRIMARY KEY (
        run_id,
        metric_name
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS network_checks (
    run_id INTEGER NOT NULL,
    check_index INTEGER NOT NULL
        CHECK (check_index >= 0),
    check_type TEXT NOT NULL,
    target TEXT NOT NULL,
    check_status TEXT NOT NULL,
    health_status TEXT NOT NULL
        CHECK (
            health_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),
    latency_ms REAL
        CHECK (
            latency_ms IS NULL
            OR latency_ms >= 0
        ),
    resolved_address TEXT,
    failure_reason TEXT,
    error_message TEXT,

    PRIMARY KEY (
        run_id,
        check_index
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS service_checks (
    run_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    label TEXT NOT NULL,
    check_status TEXT NOT NULL,
    health_status TEXT NOT NULL
        CHECK (
            health_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),
    load_state TEXT,
    active_state TEXT,
    sub_state TEXT,
    failure_reason TEXT,
    error_message TEXT,

    PRIMARY KEY (
        run_id,
        service_name
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS process_checks (
    run_id INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    label TEXT NOT NULL,
    required INTEGER NOT NULL
        CHECK (required IN (0, 1)),
    check_status TEXT NOT NULL,
    health_status TEXT NOT NULL
        CHECK (
            health_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),
    instance_count INTEGER NOT NULL
        CHECK (instance_count >= 0),
    total_cpu_percent REAL NOT NULL
        CHECK (total_cpu_percent >= 0),
    total_memory_mb REAL NOT NULL
        CHECK (total_memory_mb >= 0),
    longest_runtime_seconds REAL NOT NULL
        CHECK (longest_runtime_seconds >= 0),
    failure_reason TEXT,
    error_message TEXT,

    PRIMARY KEY (
        run_id,
        process_name
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS process_pids (
    run_id INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    pid INTEGER NOT NULL
        CHECK (pid > 0),

    PRIMARY KEY (
        run_id,
        process_name,
        pid
    ),

    FOREIGN KEY (
        run_id,
        process_name
    )
        REFERENCES process_checks (
            run_id,
            process_name
        )
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS log_checks (
    run_id INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    label TEXT NOT NULL,
    path TEXT NOT NULL,
    required INTEGER NOT NULL
        CHECK (required IN (0, 1)),
    scan_status TEXT NOT NULL,
    health_status TEXT NOT NULL
        CHECK (
            health_status IN (
                'HEALTHY',
                'WARNING',
                'CRITICAL'
            )
        ),
    total_lines_scanned INTEGER NOT NULL
        CHECK (total_lines_scanned >= 0),
    match_count INTEGER NOT NULL
        CHECK (match_count >= 0),
    failure_reason TEXT,
    error_message TEXT,

    PRIMARY KEY (
        run_id,
        source_id
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS incident_snapshots (
    run_id INTEGER NOT NULL,
    incident_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_label TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (
            severity IN (
                'WARNING',
                'CRITICAL'
            )
        ),
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL
        CHECK (occurrence_count > 0),
    resolved_at TEXT,

    PRIMARY KEY (
        run_id,
        incident_id
    ),

    FOREIGN KEY (run_id)
        REFERENCES monitoring_runs (run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS
    idx_monitoring_runs_generated_at
ON monitoring_runs (
    generated_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_monitoring_runs_host
ON monitoring_runs (
    host_name,
    generated_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_monitoring_runs_host_nocase
ON monitoring_runs (
    host_name COLLATE NOCASE,
    generated_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_monitoring_runs_status
ON monitoring_runs (
    overall_status,
    generated_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_incident_snapshots_incident
ON incident_snapshots (
    incident_id,
    last_seen_at DESC
);
"""
