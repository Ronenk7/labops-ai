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
UNIT_DIRECTORY="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
SERVICE_FILE="${UNIT_DIRECTORY}/labops-ai-api.service"
PID_FILE="${PROJECT_ROOT}/runtime/api.pid"

stop_manual_server() {
    if [[ -f "${PID_FILE}" ]]; then
        PID="$(cat "${PID_FILE}")"

        if kill -0 "${PID}" 2>/dev/null; then
            kill "${PID}"
            sleep 1
        fi

        rm -f "${PID_FILE}"
    fi
}

health_check() {
    "${PYTHON_BIN}" - <<'PY'
import json
import time
from urllib.error import URLError
from urllib.request import urlopen

from labops_ai.api.server_config import ApiServerConfigLoader

config = ApiServerConfigLoader().load()
url = f"http://{config.host}:{config.port}/api/v1/health"

for _ in range(20):
    try:
        with urlopen(url, timeout=2) as response:
            payload = json.load(response)

        if payload.get("status") == "HEALTHY":
            print(f"API healthy: {url}")
            raise SystemExit(0)
    except (OSError, URLError, ValueError):
        time.sleep(0.5)

raise SystemExit(f"API health check failed: {url}")
PY
}

install_service() {
    if [[ ! -x "${PYTHON_BIN}" ]]; then
        echo "Python executable was not found: ${PYTHON_BIN}" >&2
        exit 1
    fi

    stop_manual_server
    mkdir -p "${UNIT_DIRECTORY}"

    cat > "${SERVICE_FILE}" <<UNIT
[Unit]
Description=LabOps AI API and monitoring dashboard
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_BIN} -m labops_ai.api.server
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=5s
TimeoutStartSec=30s
TimeoutStopSec=20s
KillSignal=SIGINT
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
UNIT

    systemctl --user daemon-reload
    systemctl --user enable --now labops-ai-api.service

    health_check
    echo "LabOps AI API service installed."
}

show_status() {
    systemctl --user status \
        labops-ai-api.service \
        --no-pager
}

restart_service() {
    systemctl --user restart labops-ai-api.service
    health_check
}

show_logs() {
    journalctl --user \
        -u labops-ai-api.service \
        -n 80 \
        --no-pager
}

uninstall_service() {
    systemctl --user disable --now \
        labops-ai-api.service 2>/dev/null || true

    rm -f "${SERVICE_FILE}"

    systemctl --user daemon-reload
    systemctl --user reset-failed

    echo "LabOps AI API service removed."
}

case "${ACTION}" in
    install)
        install_service
        ;;
    status)
        show_status
        ;;
    restart)
        restart_service
        ;;
    logs)
        show_logs
        ;;
    uninstall)
        uninstall_service
        ;;
    *)
        echo \
            "Usage: $0 {install|status|restart|logs|uninstall}" \
            >&2
        exit 1
        ;;
esac
