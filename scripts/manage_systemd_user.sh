#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-install}"
INTERVAL_MINUTES="${2:-15}"

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
SERVICE_FILE="${UNIT_DIRECTORY}/labops-ai.service"
TIMER_FILE="${UNIT_DIRECTORY}/labops-ai.timer"

install_units() {
    if [[ ! -x "${PYTHON_BIN}" ]]; then
        echo "Python executable was not found: ${PYTHON_BIN}" >&2
        exit 1
    fi

    if ! [[ "${INTERVAL_MINUTES}" =~ ^[1-9][0-9]*$ ]]; then
        echo "Interval must be a positive integer." >&2
        exit 1
    fi

    mkdir -p "${UNIT_DIRECTORY}"

    cat > "${SERVICE_FILE}" <<UNIT
[Unit]
Description=LabOps AI monitoring and diagnostics run

[Service]
Type=oneshot
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_BIN} -m labops_ai
Environment=PYTHONUNBUFFERED=1
TimeoutStartSec=10min
UNIT

    cat > "${TIMER_FILE}" <<UNIT
[Unit]
Description=Schedule LabOps AI monitoring and diagnostics

[Timer]
OnBootSec=2min
OnUnitActiveSec=${INTERVAL_MINUTES}min
AccuracySec=1min
Unit=labops-ai.service

[Install]
WantedBy=timers.target
UNIT

    systemctl --user daemon-reload
    systemctl --user enable --now labops-ai.timer
    systemctl --user start labops-ai.service

    echo "LabOps AI timer installed."
    echo "Interval: ${INTERVAL_MINUTES} minutes"
}

show_status() {
    systemctl --user status \
        labops-ai.timer \
        --no-pager

    echo
    systemctl --user list-timers \
        labops-ai.timer \
        --no-pager
}

uninstall_units() {
    systemctl --user disable --now \
        labops-ai.timer 2>/dev/null || true

    rm -f "${SERVICE_FILE}" "${TIMER_FILE}"

    systemctl --user daemon-reload
    systemctl --user reset-failed

    echo "LabOps AI timer removed."
}

case "${ACTION}" in
    install)
        install_units
        ;;
    status)
        show_status
        ;;
    uninstall)
        uninstall_units
        ;;
    *)
        echo "Usage: $0 {install|status|uninstall} [minutes]" >&2
        exit 1
        ;;
esac
