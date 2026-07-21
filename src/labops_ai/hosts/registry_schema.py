"""SQLite schema for the central host registry."""


HOST_REGISTRY_SCHEMA_VERSION = 1


HOST_REGISTRY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS host_registry_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS monitored_hosts (
    host_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(host_id)) > 0),

    host_name TEXT NOT NULL
        CHECK (length(trim(host_name)) > 0),

    address TEXT NOT NULL
        CHECK (length(trim(address)) > 0),

    operating_system TEXT NOT NULL
        CHECK (length(trim(operating_system)) > 0),

    architecture TEXT NOT NULL
        CHECK (length(trim(architecture)) > 0),

    agent_version TEXT NOT NULL
        CHECK (length(trim(agent_version)) > 0),

    registered_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,

    CHECK (last_seen_at >= registered_at)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS
    idx_monitored_hosts_last_seen
ON monitored_hosts (
    last_seen_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_monitored_hosts_name
ON monitored_hosts (
    host_name COLLATE NOCASE
);
"""
