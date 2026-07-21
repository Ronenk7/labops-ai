#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-install}"

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"
PROJECT_ROOT="$(
    cd "${SCRIPT_DIR}/.."
    pwd
)"

PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
CONFIG_FILE="${PROJECT_ROOT}/config/host_agent.json"

SERVICE_NAME="labops-ai-agent.service"
UNIT_DIRECTORY="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
SERVICE_FILE="${UNIT_DIRECTORY}/${SERVICE_NAME}"


render_service() {
    cat <<UNIT
[Unit]
Description=LabOps AI remote host heartbeat agent
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_BIN} -m labops_ai.agent --continuous --config ${CONFIG_FILE}
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Restart=on-failure
RestartSec=5s
TimeoutStartSec=20s
TimeoutStopSec=20s
KillSignal=SIGTERM
NoNewPrivileges=true
PrivateTmp=true
UMask=0077

[Install]
WantedBy=default.target
UNIT
}


validate_runtime() {
    if [[ ! -x "${PYTHON_BIN}" ]]; then
        echo \
            "Python executable was not found: ${PYTHON_BIN}" \
            >&2
        exit 1
    fi

    if [[ ! -f "${CONFIG_FILE}" ]]; then
        echo \
            "Agent configuration was not found: ${CONFIG_FILE}" \
            >&2
        exit 1
    fi
}


require_user_systemd() {
    if ! systemctl --user show-environment \
        >/dev/null 2>&1
    then
        echo \
            "The systemd user manager is unavailable." \
            >&2
        echo \
            "Enable systemd in WSL before installing the service." \
            >&2
        exit 1
    fi
}


verify_service_file() {
    if command -v systemd-analyze \
        >/dev/null 2>&1
    then
        systemd-analyze \
            --user \
            verify \
            "${SERVICE_FILE}"
    fi
}


require_api_available() {
    "${PYTHON_BIN}" - "${CONFIG_FILE}" <<'PY'
import json
import sys
import time
from urllib.request import urlopen

from labops_ai.agent import HostAgentConfigLoader


config = HostAgentConfigLoader(
    sys.argv[1]
).load()

url = (
    f"{config.server.base_url}"
    "/api/v1/health"
)

for _ in range(20):
    try:
        with urlopen(
            url,
            timeout=(
                config.server
                .request_timeout_seconds
            ),
        ) as response:
            payload = json.load(response)

        if payload.get("status") == "HEALTHY":
            print(f"Central API healthy: {url}")
            raise SystemExit(0)
    except (OSError, ValueError):
        time.sleep(0.5)

raise SystemExit(
    f"Central API health check failed: {url}"
)
PY
}


resolve_host_id() {
    "${PYTHON_BIN}" - "${CONFIG_FILE}" <<'PY'
import sys

from labops_ai.agent import (
    HostAgentConfigLoader,
    LocalHostProviders,
)


config = HostAgentConfigLoader(
    sys.argv[1]
).load()

host_id = (
    config.identity.host_id_override
    or LocalHostProviders().host_name()
)

print(host_id)
PY
}


read_last_seen() {
    local host_id="$1"

    "${PYTHON_BIN}" - \
        "${CONFIG_FILE}" \
        "${host_id}" <<'PY'
import json
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

from labops_ai.agent import HostAgentConfigLoader


config = HostAgentConfigLoader(
    sys.argv[1]
).load()
host_id = sys.argv[2]

url = (
    f"{config.server.base_url}"
    "/api/v1/hosts/"
    f"{quote(host_id, safe='')}"
)

try:
    with urlopen(
        url,
        timeout=(
            config.server
            .request_timeout_seconds
        ),
    ) as response:
        payload = json.load(response)
except HTTPError as error:
    if error.code == 404:
        raise SystemExit(0)

    raise
except (OSError, ValueError):
    raise SystemExit(0)

last_seen_at = payload.get("last_seen_at")

if isinstance(last_seen_at, str):
    print(last_seen_at)
PY
}


wait_for_fresh_heartbeat() {
    local host_id="$1"
    local baseline_last_seen="${2:-}"

    "${PYTHON_BIN}" - \
        "${CONFIG_FILE}" \
        "${host_id}" \
        "${baseline_last_seen}" <<'PY'
import json
import sys
import time
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

from labops_ai.agent import HostAgentConfigLoader


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


config = HostAgentConfigLoader(
    sys.argv[1]
).load()
host_id = sys.argv[2]
baseline_text = sys.argv[3]

baseline_time = (
    parse_timestamp(baseline_text)
    if baseline_text
    else None
)

url = (
    f"{config.server.base_url}"
    "/api/v1/hosts/"
    f"{quote(host_id, safe='')}"
)

for _ in range(50):
    try:
        with urlopen(
            url,
            timeout=(
                config.server
                .request_timeout_seconds
            ),
        ) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code != 404:
            pass

        time.sleep(0.5)
        continue
    except (OSError, ValueError):
        time.sleep(0.5)
        continue

    current_text = payload.get(
        "last_seen_at"
    )

    if (
        payload.get("host_id") == host_id
        and isinstance(current_text, str)
    ):
        current_time = parse_timestamp(
            current_text
        )

        if (
            baseline_time is None
            or current_time > baseline_time
        ):
            print(
                "Fresh Agent heartbeat registered: "
                f"{url}"
            )
            print(
                "last_seen_at="
                f"{current_text}"
            )
            raise SystemExit(0)

    time.sleep(0.5)

raise SystemExit(
    "Fresh Agent heartbeat registration "
    f"check failed: {url}"
)
PY
}


show_failure_diagnostics() {
    systemctl --user status \
        "${SERVICE_NAME}" \
        --no-pager \
        --full \
        >&2 || true

    journalctl --user \
        -u "${SERVICE_NAME}" \
        -n 50 \
        --no-pager \
        >&2 || true
}


activate_service() {
    local operation="$1"

    if ! systemctl --user \
        "${operation}" \
        "${SERVICE_NAME}"
    then
        show_failure_diagnostics
        exit 1
    fi

    if ! systemctl --user is-active \
        --quiet \
        "${SERVICE_NAME}"
    then
        echo \
            "Agent service is not active after ${operation}." \
            >&2
        show_failure_diagnostics
        exit 1
    fi
}


install_service() {
    validate_runtime
    require_user_systemd
    require_api_available

    local host_id
    local baseline_last_seen

    host_id="$(resolve_host_id)"
    baseline_last_seen="$(
        read_last_seen "${host_id}"
    )"

    mkdir -p "${UNIT_DIRECTORY}"
    render_service > "${SERVICE_FILE}"

    verify_service_file

    systemctl --user daemon-reload
    systemctl --user reset-failed \
        "${SERVICE_NAME}" \
        2>/dev/null || true

    systemctl --user enable \
        "${SERVICE_NAME}"

    activate_service restart

    wait_for_fresh_heartbeat \
        "${host_id}" \
        "${baseline_last_seen}"

    echo \
        "LabOps AI Agent service installed."
}


start_service() {
    validate_runtime
    require_user_systemd
    require_api_available

    if systemctl --user is-active \
        --quiet \
        "${SERVICE_NAME}"
    then
        echo \
            "LabOps AI Agent service is already active."
        return
    fi

    local host_id
    local baseline_last_seen

    host_id="$(resolve_host_id)"
    baseline_last_seen="$(
        read_last_seen "${host_id}"
    )"

    activate_service start

    wait_for_fresh_heartbeat \
        "${host_id}" \
        "${baseline_last_seen}"

    echo \
        "LabOps AI Agent service started."
}


stop_service() {
    require_user_systemd

    systemctl --user stop \
        "${SERVICE_NAME}"

    if systemctl --user is-active \
        --quiet \
        "${SERVICE_NAME}"
    then
        echo \
            "Agent service remained active after stop." \
            >&2
        show_failure_diagnostics
        exit 1
    fi

    echo \
        "LabOps AI Agent service stopped."
}


restart_service() {
    validate_runtime
    require_user_systemd
    require_api_available

    local host_id
    local baseline_last_seen

    host_id="$(resolve_host_id)"
    baseline_last_seen="$(
        read_last_seen "${host_id}"
    )"

    activate_service restart

    wait_for_fresh_heartbeat \
        "${host_id}" \
        "${baseline_last_seen}"

    echo \
        "LabOps AI Agent service restarted."
}


show_status() {
    require_user_systemd

    systemctl --user status \
        "${SERVICE_NAME}" \
        --no-pager \
        --full
}


show_logs() {
    require_user_systemd

    journalctl --user \
        -u "${SERVICE_NAME}" \
        -n 100 \
        --no-pager
}


uninstall_service() {
    require_user_systemd

    systemctl --user disable --now \
        "${SERVICE_NAME}" \
        2>/dev/null || true

    rm -f "${SERVICE_FILE}"

    systemctl --user daemon-reload
    systemctl --user reset-failed

    echo \
        "LabOps AI Agent service removed."
}


case "${ACTION}" in
    render)
        render_service
        ;;
    install)
        install_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    uninstall)
        uninstall_service
        ;;
    *)
        echo \
            "Usage: $0 {render|install|start|stop|restart|status|logs|uninstall}" \
            >&2
        exit 1
        ;;
esac
